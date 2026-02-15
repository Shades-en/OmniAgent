from __future__ import annotations

import asyncio
import pymongo
from beanie import Document
from bson import ObjectId
from pymongo import IndexModel

from datetime import datetime, timezone
from pydantic import Field

from opentelemetry.trace import SpanKind

from omniagent.exceptions import (
    UserRetrievalError,
    UserDeletionError,
)
from omniagent.utils.tracing import trace_operation, CustomSpanKinds
from omniagent.schemas.mongo.message import Message
from omniagent.schemas.mongo.summary import Summary
from omniagent.types.user import UserType


class User(Document):
    cookie_id: str = Field(..., min_length=1)
    category: UserType = UserType.GUEST
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("cookie_id", pymongo.ASCENDING)],
                unique=True,
            )
        ]
    
    @classmethod
    async def get_by_id(cls, user_id: str) -> User | None:
        """Retrieve a user by their MongoDB document ID."""
        try:
            return await cls.get(ObjectId(user_id))
        except Exception as e:
            raise UserRetrievalError(
                "Failed to retrieve user by ID",
                details=f"user_id={user_id}, error={str(e)}"
            )
    
    @classmethod
    async def get_by_cookie_id(cls, cookie_id: str) -> User | None:
        """Retrieve a user by their cookie ID."""
        try:
            return await cls.find_one(cls.cookie_id == cookie_id)
        except Exception as e:
            raise UserRetrievalError(
                "Failed to retrieve user by cookie ID",
                details=f"cookie_id={cookie_id}, error={str(e)}"
            )
    
    @classmethod
    async def get_by_id_or_cookie(cls, user_id: str | None, cookie_id: str) -> User | None:
        """
        Retrieve a user by ID or cookie ID.
        
        Args:
            user_id: MongoDB document ID of the user (optional)
            cookie_id: Cookie ID of the user
            
        Returns:
            User object if found, None otherwise        
        """
        if user_id:
            return await cls.get_by_id(user_id)
        else:
            return await cls.get_by_cookie_id(cookie_id)
    
    @classmethod
    async def delete_by_id_or_cookie(cls, user_id: str | None, cookie_id: str, cascade: bool = True) -> dict:
        """
        Delete a user by ID or cookie ID and optionally cascade delete all related sessions.
        
        Args:
            user_id: MongoDB document ID of the user (optional)
            cookie_id: Cookie ID of the user
            cascade: If True, also delete all sessions (and their messages/turns/summaries)
            
        Returns:
            Dictionary with deletion info: {
                "user_deleted": bool,
                "sessions_deleted": int,
                "messages_deleted": int,
                "turns_deleted": int,
                "summaries_deleted": int
            }
            
        Raises:
            UserDeletionFailedException: If deletion fails
        """
        if user_id:
            return await cls.delete_by_id(user_id, cascade=cascade)
        else:
            return await cls.delete_by_cookie_id(cookie_id, cascade=cascade)
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def delete_by_cookie_id(cls, cookie_id: str, cascade: bool = True) -> dict:
        """
        Delete a user by cookie ID and optionally cascade delete all related sessions.
        
        Args:
            cookie_id: Cookie ID of the user to delete
            cascade: If True, also delete all sessions (and their messages/turns/summaries)
            
        Returns:
            Dictionary with deletion info: {
                "user_deleted": bool,
                "sessions_deleted": int,
                "messages_deleted": int,
                "turns_deleted": int,
                "summaries_deleted": int
            }
            
        Raises:
            UserDeletionFailedException: If deletion fails
        
        Traced as INTERNAL span for database transaction.
        """
        try:
            user = await cls.get_by_cookie_id(cookie_id)
            if not user:
                return {
                    "user_deleted": False,
                    "sessions_deleted": 0,
                    "messages_deleted": 0,
                    "turns_deleted": 0,
                    "summaries_deleted": 0
                }
            
            return await cls._delete_user_with_sessions(user, cascade)
            
        except Exception as e:
            raise UserDeletionError(
                "Failed to delete user by cookie ID",
                details=f"cookie_id={cookie_id}, cascade={cascade}, error={str(e)}"
            )
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def delete_by_id(cls, user_id: str, cascade: bool = True) -> dict:
        """
        Delete a user by ID and optionally cascade delete all related sessions.
        
        Args:
            user_id: MongoDB document ID of the user to delete
            cascade: If True, also delete all sessions (and their messages/turns/summaries)
            
        Returns:
            Dictionary with deletion info: {
                "user_deleted": bool,
                "sessions_deleted": int,
                "messages_deleted": int,
                "turns_deleted": int,
                "summaries_deleted": int
            }
            
        Raises:
            UserDeletionFailedException: If deletion fails
        
        Traced as INTERNAL span for database transaction.
        """
        try:
            user = await cls.get_by_id(user_id)
            if not user:
                return {
                    "user_deleted": False,
                    "sessions_deleted": 0,
                    "messages_deleted": 0,
                    "turns_deleted": 0,
                    "summaries_deleted": 0
                }
            
            return await cls._delete_user_with_sessions(user, cascade)
            
        except Exception as e:
            raise UserDeletionError(
                "Failed to delete user by ID",
                details=f"user_id={user_id}, cascade={cascade}, error={str(e)}"
            )
    
    @classmethod
    @trace_operation(kind=SpanKind.INTERNAL, open_inference_kind=CustomSpanKinds.DATABASE.value)
    async def _delete_user_with_sessions(cls, user: User, cascade: bool) -> dict:
        """
        Internal helper to delete user and optionally cascade delete sessions.
        
        Args:
            user: User object to delete
            cascade: If True, delete all sessions with their related data
            
        Returns:
            Dictionary with deletion counts
        
        Traced as INTERNAL span for database transaction with cascade delete.
        """
        from omniagent.db import MongoDB
        from omniagent.schemas.mongo.session import Session

        client = MongoDB.get_client()
        
        async with client.start_session() as session_txn:
            try:
                async with await session_txn.start_transaction():
                    if cascade:
                        # Delete user, sessions, and their related data in parallel
                        delete_results = await asyncio.gather(
                            user.delete(session=session_txn),
                            Message.find({"session.user.$id": user.id}).delete(session=session_txn),
                            Summary.find({"session.user.$id": user.id}).delete(session=session_txn),
                            Session.find(Session.user.id == user.id).delete(session=session_txn)
                        )
                        
                        messages_deleted = delete_results[1].deleted_count if delete_results[1] else 0
                        summaries_deleted = delete_results[2].deleted_count if delete_results[2] else 0
                        sessions_deleted = delete_results[3].deleted_count if delete_results[3] else 0
                    else:
                        # Delete user and sessions in parallel, not their related data
                        delete_results = await asyncio.gather(
                            user.delete(session=session_txn),
                            Session.find(Session.user.id == user.id).delete(session=session_txn)
                        )
                        sessions_deleted = delete_results[1].deleted_count if delete_results[1] else 0
                        messages_deleted = 0
                        summaries_deleted = 0
                    
                    return {
                        "user_deleted": True,
                        "sessions_deleted": sessions_deleted,
                        "messages_deleted": messages_deleted,
                        "summaries_deleted": summaries_deleted
                    }
                    
            except Exception as e:
                raise UserDeletionError(
                    "Failed to delete user with sessions",
                    details=f"user_id={user.id}, cascade={cascade}, error={str(e)}"
                )
