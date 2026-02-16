from __future__ import annotations

from beanie import Document, Link
import pymongo
from bson import ObjectId

from datetime import datetime, timezone
from pydantic import Field
from typing import List, TYPE_CHECKING
import asyncio

from opentelemetry.trace import SpanKind

if TYPE_CHECKING:
    from omniagent.schemas.mongo.message import Message
    from omniagent.schemas.mongo.summary import Summary

from omniagent.schemas.mongo.user import User
from omniagent.types.message import MessageDTO
from omniagent.exceptions import (
    SessionRetrievalError,
    SessionCreationError,
    SessionUpdateError,
    SessionDeletionError,
    MessageCreationError,
)
from omniagent.config import DEFAULT_SESSION_NAME, DEFAULT_SESSION_PAGE_SIZE
from omniagent.utils.tracing import trace_method, trace_operation, CustomSpanKinds
from omniagent.db.document_models import get_message_model, get_summary_model
from omniagent.schemas.mongo.public_dict import PublicDictMixin


class Session(PublicDictMixin, Document):
    PUBLIC_EXCLUDE = {"user"}

    name: str = Field(default_factory=lambda: DEFAULT_SESSION_NAME)
    latest_turn_number: int = Field(...)
    user: Link[User]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    starred: bool = Field(default=False)

    class Settings:
        name = "sessions"
        indexes = [
            [("user.$id", pymongo.ASCENDING), ("updated_at", pymongo.DESCENDING)]
        ]
    
    @classmethod
    async def get_by_id(cls, session_id: str, user_id: str) -> Session | None:
        """
        Retrieve a session by its MongoDB document ID, filtered by user_id.
        This ensures users can only access their own sessions.
        
        Args:
            session_id: The session's MongoDB document ID
            user_id: The user's MongoDB document ID for authorization
            
        Returns:
            Session if found and belongs to user, None otherwise
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            user_obj_id = ObjectId(user_id)
            session_obj_id = ObjectId(session_id)
            
            # Direct query with user filter - no aggregation needed
            session = await cls.find_one(
                cls.id == session_obj_id,
                cls.user.id == user_obj_id
            )
            return session
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to retrieve session by ID",
                details=f"session_id={session_id}, user_id={user_id}, error={str(e)}"
            )
    
    @classmethod
    async def get_by_id_and_client_id(cls, session_id: str, client_id: str) -> Session | None:
        """
        Retrieve a session by its MongoDB document ID, filtered by user's client_id.
        This is a fallback method when user_id is not available.
        
        Args:
            session_id: The session's MongoDB document ID
            client_id: The user's client ID for authorization
            
        Returns:
            Session if found and belongs to user, None otherwise
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "_id": ObjectId(session_id)
                    }
                },
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user.$id",
                        "foreignField": "_id",
                        "as": "user_data"
                    }
                },
                {
                    "$unwind": "$user_data"
                },
                {
                    "$match": {
                        "user_data.client_id": client_id
                    }
                }
            ]
            
            results = await cls.aggregate(pipeline).to_list()
            if not results:
                return None
            return cls.model_validate(results[0])
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to retrieve session by ID and client_id",
                details=f"session_id={session_id}, client_id={client_id}, error={str(e)}"
            )
    
    @classmethod
    @trace_method(
        kind=SpanKind.INTERNAL,
        graph_node_id="db_create_session_with_user",
        capture_input=False,
        capture_output=False
    )
    async def create_with_user(
        cls,
        client_id: str,
        session_id: str,
        session_name: str = DEFAULT_SESSION_NAME
    ) -> Session:
        """
        Create a new session with a new user atomically using MongoDB transaction.
        
        Args:
            client_id: Client ID for the new user
            session_id: MongoDB ObjectId string for the session (required)
            session_name: Name for the session
            
        Returns:
            Created Session document
            
        Raises:
            SessionCreationError: If transaction fails or session_id not provided
        
        Traced as INTERNAL span for database transaction.
        """
        from omniagent.db import MongoDB

        if not session_id:
            raise SessionCreationError(
                "session_id is required to create a session",
                details="session_id parameter must be provided"
            )

        client = MongoDB.get_client()

        if not session_name:
            session_name = DEFAULT_SESSION_NAME
        
        async with client.start_session() as session_txn:
            try:
                async with await session_txn.start_transaction():
                    # Create new user
                    new_user = User(client_id=client_id)
                    await new_user.insert(session=session_txn)
                    
                    # Create and save session with provided session_id
                    new_session = cls(
                        id=ObjectId(session_id),
                        name=session_name,
                        user=new_user,
                        latest_turn_number=0
                    )
                    await new_session.insert(session=session_txn)
                    
                    return new_session
                    
            except Exception as e:
                # Transaction will automatically abort on exception
                raise SessionCreationError(
                    "Failed to create session with user in transaction",
                    details=f"client_id={client_id}, session_id={session_id}, session_name={session_name}, error={str(e)}"
                )
    
    @classmethod
    async def create_for_existing_user(
        cls,
        user: User,
        session_id: str,
        session_name: str = DEFAULT_SESSION_NAME
    ) -> Session:
        """
        Create a new session for an existing user.
        
        Args:
            user: Existing User document (must have an id)
            session_id: MongoDB ObjectId string for the session (required)
            session_name: Name for the session
            
        Returns:
            Created Session document
            
        Raises:
            SessionCreationError: If session creation fails, user has no id, or session_id not provided
        """
        if not user.id:
            raise SessionCreationError(
                "Cannot create session for user without id",
                details="User must be saved to database before creating a session"
            )

        if not session_id:
            raise SessionCreationError(
                "session_id is required to create a session",
                details="session_id parameter must be provided"
            )
        
        try:
            if not session_name:
                session_name = DEFAULT_SESSION_NAME
                
            new_session = cls(
                id=ObjectId(session_id),
                name=session_name,
                user=user,
                latest_turn_number=0
            )
            await new_session.insert()
            return new_session
            
        except Exception as e:
            raise SessionCreationError(
                "Failed to create session for existing user",
                details=f"user_id={user.id}, session_id={session_id}, session_name={session_name}, error={str(e)}"
            )

    async def _update_latest_turn_number(self, turn_number: int, session=None) -> None:
        """
        Update the latest turn number and updated_at timestamp for a session.
        
        Args:
            session_id: MongoDB document ID of the session
            turn_number: New latest turn number
            session: Optional MongoDB session for transaction support
            
        Raises:
            SessionUpdateError: If update fails
        """
        try:
            if not self.id:
                raise SessionUpdateError(
                    "Cannot update latest turn number for non-existent session",
                    details=f"session_id={self.id}, turn_number={turn_number}"
                )
            
            self.latest_turn_number = turn_number
            self.updated_at = datetime.now(timezone.utc)
            if session:
                await self.save(session=session)
            else:
                await self.save()
            
        except Exception as e:
            raise SessionUpdateError(
                "Failed to update latest turn number for session",
                details=f"session_id={self.id}, turn_number={turn_number}, error={str(e)}"
            )
    
    async def update_name(self, new_name: str) -> None:
        """
        Update the session name.
        
        Args:
            new_name: New name for the session
            
        Raises:
            SessionUpdateError: If update fails
        """
        if not self.id:
            raise SessionUpdateError(
                "Cannot update name for unsaved session",
                details="Session must be saved to database before updating name"
            )
        
        try:
            self.name = new_name
            await self.save()
            
        except Exception as e:
            raise SessionUpdateError(
                "Failed to update session name",
                details=f"session_id={self.id}, new_name={new_name}, error={str(e)}"
            )
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def update_starred(cls, session_id: str, starred: bool, user_id: str) -> dict:
        """
        Update the starred status for a session.
        
        Args:
            session_id: The session ID to update
            starred: Whether the session should be starred (True) or unstarred (False)
            user_id: The user's MongoDB document ID for authorization
            
        Returns:
            Dictionary with update info: {
                "session_updated": bool,
                "session_id": str,
                "starred": bool
            }
            
        Raises:
            SessionUpdateError: If update fails
        
        Traced as INTERNAL span for database operation.
        """
        try:
            session = await cls.get_by_id(session_id, user_id)
            
            if not session:
                raise SessionUpdateError(
                    "Session not found",
                    details=f"session_id={session_id}"
                )
            
            session.starred = starred
            await session.save()
            
            return {
                "session_updated": True,
                "session_id": session_id,
                "starred": starred
            }
                    
        except SessionUpdateError:
            raise
        except Exception as e:
            raise SessionUpdateError(
                "Failed to update session starred status",
                details=f"session_id={session_id}, starred={starred}, error={str(e)}"
            )
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def delete_all_by_user_id(cls, user_id: str) -> dict:
        """
        Delete all sessions for a user by user_id and all related documents (messages, summaries).
        
        Args:
            user_id: The user's MongoDB document ID
        
        Returns:
            Dictionary with deletion counts: {
                "sessions_deleted": int,
                "messages_deleted": int, 
                "summaries_deleted": int
            }
        
        Raises:
            SessionDeletionError: If deletion fails
        
        Traced as INTERNAL span for database transaction with cascade delete.
        """
        from omniagent.db import MongoDB
        
        try:
            MessageModel = get_message_model()
            SummaryModel = get_summary_model()
            obj_id = ObjectId(user_id)
            
            # Check if user has any sessions
            sessions = await cls.find(cls.user.id == obj_id).to_list()
            if not sessions:
                return {
                    "sessions_deleted": 0,
                    "messages_deleted": 0,
                    "summaries_deleted": 0
                }
            
            client = MongoDB.get_client()
            
            async with client.start_session() as session_txn:
                async with await session_txn.start_transaction():
                    # Delete all sessions, messages, and summaries in parallel
                    delete_results = await asyncio.gather(
                        cls.find(cls.user.id == obj_id).delete(session=session_txn),
                        MessageModel.find({"session.user.$id": obj_id}).delete(session=session_txn),
                        SummaryModel.find({"session.user.$id": obj_id}).delete(session=session_txn)
                    )
                    
                    sessions_deleted = delete_results[0].deleted_count if delete_results[0] else 0
                    messages_deleted = delete_results[1].deleted_count if delete_results[1] else 0
                    summaries_deleted = delete_results[2].deleted_count if delete_results[2] else 0
                    
                    return {
                        "sessions_deleted": sessions_deleted,
                        "messages_deleted": messages_deleted,
                        "summaries_deleted": summaries_deleted
                    }
                    
        except Exception as e:
            raise SessionDeletionError(
                "Failed to delete all sessions for user",
                details=f"user_id={user_id}, error={str(e)}"
            )
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def delete_with_related(cls, session_id: str, user_id: str) -> dict:
        """
        Delete session and all related documents (messages, summaries) in a transaction.
        This prevents orphaned documents with dangling references.
        
        Args:
            session_id: MongoDB document ID of the session to delete
            user_id: The user's MongoDB document ID for authorization
        
        Returns:
            Dictionary with deletion counts: {
                "messages_deleted": int, 
                "summaries_deleted": int,
                "session_deleted": bool
            }
        
        Raises:
            SessionDeletionError: If deletion fails
        
        Traced as INTERNAL span for database transaction with cascade delete.
        """
        from omniagent.db import MongoDB
        
        try:
            MessageModel = get_message_model()
            SummaryModel = get_summary_model()
            session = await cls.get_by_id(session_id, user_id)
            
            if not session:
                return {
                    "messages_deleted": 0,
                    "summaries_deleted": 0,
                    "session_deleted": False
                }
            
            client = MongoDB.get_client()
            session_obj_id = session.id  # Get the session's ObjectId
            
            async with client.start_session() as session_txn:
                async with await session_txn.start_transaction():
                    # Delete session, messages, and summaries in parallel
                    delete_results = await asyncio.gather(
                        session.delete(session=session_txn),
                        MessageModel.find(MessageModel.session._id == session_obj_id).delete(session=session_txn),
                        SummaryModel.find(SummaryModel.session._id == session_obj_id).delete(session=session_txn)
                    )
                    
                    messages_deleted = delete_results[1].deleted_count if delete_results[1] else 0
                    summaries_deleted = delete_results[2].deleted_count if delete_results[2] else 0
                    
                    return {
                        "messages_deleted": messages_deleted,
                        "summaries_deleted": summaries_deleted,
                        "session_deleted": True
                    }
                    
        except Exception as e:
            raise SessionDeletionError(
                "Failed to delete session with related documents",
                details=f"session_id={session_id}, error={str(e)}"
            )
    
    @trace_method(
        kind=SpanKind.INTERNAL,
        graph_node_id="db_insert_messages",
        capture_input=False,
        capture_output=False
    )
    async def insert_messages(
        self, 
        messages: List[MessageDTO],
        turn_number: int,
        previous_summary: Summary,
    ) -> List[Message]:
        """
        Bulk insert messages for this session with turn information.
        
        Since this is a single bulk insert operation, no transaction is needed.
        MongoDB's insert_many is atomic for a single collection.
        
        Args:
            messages: List of MessageDTO objects to insert
            turn_number: The turn number for these messages
            previous_summary: Optional previous Summary document for this turn
            
        Returns:
            List of inserted Message documents
            
        Raises:
            MessageCreationError: If bulk insert fails
        
        Traced as INTERNAL span for database operation.
        """
        if not self.id:
            raise MessageCreationError(
                "Cannot insert messages for unsaved session",
                details="Session must be saved to database before inserting messages"
            )
        
        if not messages:
            return []
        
        try:
            MessageModel = get_message_model()

            # Convert MessageDTOs to Message documents
            message_docs = []
            for msg_dto in messages:
                message_doc = MessageModel(
                    role=msg_dto.role.value,  # Extract string value from enum
                    parts=msg_dto.parts,
                    metadata=msg_dto.metadata,
                    turn_number=turn_number,
                    previous_summary=previous_summary,
                    session=self,
                    created_at=msg_dto.created_at,
                    client_message_id=msg_dto.id  # Store frontend ID separately, MongoDB auto-generates _id
                )
                message_docs.append(message_doc)

            # Insert messages using Beanie with transaction - shield from cancellation
            from omniagent.db import MongoDB

            async def _do_insert():
                client = MongoDB.get_client()
                async with client.start_session() as session_txn:
                    async with await session_txn.start_transaction():
                        await MessageModel.insert_many(message_docs, session=session_txn)
                        await self._update_latest_turn_number(turn_number, session=session_txn)
            
            await _do_insert()
            
            return message_docs
            
        except Exception as e:
            raise MessageCreationError(
                "Failed to bulk insert messages for session",
                details=f"session_id={self.id}, turn_number={turn_number}, message_count={len(messages)}, error={str(e)}"
            )
    
    @classmethod
    async def get_paginated_by_user_client_id(
        cls,
        client_id: str,
        page: int = 1,
        page_size: int = DEFAULT_SESSION_PAGE_SIZE
    ) -> List[Session]:
        """
        Get paginated sessions for a user by client ID, sorted by most recent first.
        Uses MongoDB aggregation with $lookup to join with users collection.
        
        Args:
            client_id: The user's client ID
            page: Page number (1-indexed)
            page_size: Number of sessions per page
            
        Returns:
            List of Session documents sorted by most recent first
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            skip = (page - 1) * page_size
            
            # Aggregation pipeline to lookup user by client_id and get sessions
            pipeline = [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user.$id",
                        "foreignField": "_id",
                        "as": "user_data"
                    }
                },
                {
                    "$unwind": "$user_data"
                },
                {
                    "$match": {
                        "user_data.client_id": client_id
                    }
                },
                {
                    "$sort": {"updated_at": -1}  # Most recently updated first
                },
                {
                    "$skip": skip
                },
                {
                    "$limit": page_size
                }
            ]
            
            sessions = await cls.aggregate(pipeline).to_list()
            
            # Convert aggregation results back to Session documents
            return [cls.model_validate(session) for session in sessions]
            
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to retrieve paginated sessions for user by client_id",
                details=f"client_id={client_id}, page={page}, page_size={page_size}, error={str(e)}"
            )
    
    @classmethod
    async def get_all_by_user_client_id(cls, client_id: str) -> List[Session]:
        """
        Get all sessions for a user by client ID, sorted by most recent first.
        Uses MongoDB aggregation with $lookup to join with users collection.
        
        Args:
            client_id: The user's client ID
            
        Returns:
            List of all Session documents sorted by most recent first
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            # Aggregation pipeline to lookup user by client_id and get all sessions
            pipeline = [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user.$id",
                        "foreignField": "_id",
                        "as": "user_data"
                    }
                },
                {
                    "$unwind": "$user_data"
                },
                {
                    "$match": {
                        "user_data.client_id": client_id
                    }
                },
                {
                    "$sort": {"updated_at": -1}  # Most recently updated first
                }
            ]
            
            sessions = await cls.aggregate(pipeline).to_list()
            
            # Convert aggregation results back to Session documents
            return [cls.model_validate(session) for session in sessions]
            
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to retrieve all sessions for user by client_id",
                details=f"client_id={client_id}, error={str(e)}"
            )
    
    @classmethod
    async def count_by_user_client_id(cls, client_id: str) -> int:
        """
        Get the total count of sessions for a user by client ID.
        Uses MongoDB aggregation with $lookup to join with users collection.
        
        Args:
            client_id: The user's client ID
            
        Returns:
            Total count of sessions for the user
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            # Aggregation pipeline to lookup user by client_id and count sessions
            pipeline = [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user.$id",
                        "foreignField": "_id",
                        "as": "user_data"
                    }
                },
                {
                    "$unwind": "$user_data"
                },
                {
                    "$match": {
                        "user_data.client_id": client_id
                    }
                },
                {
                    "$count": "total"
                }
            ]
            
            result = await cls.aggregate(pipeline).to_list()
            
            # If no sessions found, return 0
            return result[0]["total"] if result else 0
            
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to count sessions for user by client_id",
                details=f"client_id={client_id}, error={str(e)}"
            )
    
    @classmethod
    async def get_starred_by_user_client_id(cls, client_id: str) -> List[Session]:
        """
        Get all starred sessions for a user by client ID, sorted by most recently updated first.
        Uses MongoDB aggregation with $lookup to join with users collection.
        
        Args:
            client_id: The user's client ID
            
        Returns:
            List of starred Session documents sorted by most recently updated first
            
        Raises:
            SessionRetrievalError: If retrieval fails
        """
        try:
            # Aggregation pipeline to lookup user by client_id and get starred sessions
            pipeline = [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user.$id",
                        "foreignField": "_id",
                        "as": "user_data"
                    }
                },
                {
                    "$unwind": "$user_data"
                },
                {
                    "$match": {
                        "user_data.client_id": client_id,
                        "starred": True
                    }
                },
                {
                    "$sort": {"updated_at": -1}  # Most recently updated first
                }
            ]
            
            sessions = await cls.aggregate(pipeline).to_list()
            
            # Convert aggregation results back to Session documents
            return [cls.model_validate(session) for session in sessions]
            
        except Exception as e:
            raise SessionRetrievalError(
                "Failed to retrieve starred sessions for user by client_id",
                details=f"client_id={client_id}, error={str(e)}"
            )

        
