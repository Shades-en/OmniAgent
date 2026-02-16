"""
MongoDB-specific SessionManager implementation using Beanie ODM.
"""

import asyncio
from typing import List, Tuple

import logging

from omniagent.session.base import SessionManager
from omniagent.ai.providers import get_llm_provider
from omniagent.types.message import MessageDTO
from omniagent.schemas.mongo import User, Session, Message, Summary
from omniagent.config import MAX_TURNS_TO_FETCH, LLM_PROVIDER
from omniagent.exceptions import (
    SessionNotFoundError,
    UserNotFoundError,
)
from omniagent.utils.tracing import trace_method, CustomSpanKinds
from omniagent.ai.providers.utils import StreamCallback, stream_fallback_response
from omniagent.db.mongo import MongoDB

logger = logging.getLogger(__name__)


class MongoSessionManager(SessionManager):
    """
    MongoDB-specific implementation of SessionManager using Beanie ODM.
    
    Implements database operations for fetching and persisting user sessions,
    messages, and summaries in MongoDB.
    """

    @classmethod
    async def initialize(
        cls,
        db_name: str | None = None,
        srv_uri: str | None = None,
        allow_index_dropping: bool = False,
    ) -> None:
        """
        Initialize MongoDB connection and register Beanie document models.
        
        This should be called once during application startup (e.g., FastAPI lifespan).
        
        Args:
            db_name: Database name (defaults to MONGO_DB_NAME env var)
            srv_uri: Full MongoDB SRV URI (defaults to MONGO_SRV_URI env var)
            allow_index_dropping: Whether to allow dropping indexes on init
        
        Example:
            ```python
            @asynccontextmanager
            async def lifespan(app: FastAPI):
                await MongoSessionManager.initialize()
                yield
                await MongoSessionManager.shutdown()
            ```
        """
        await MongoDB.init(
            db_name=db_name,
            srv_uri=srv_uri,
            allow_index_dropping=allow_index_dropping,
        )

    @classmethod
    async def shutdown(cls) -> None:
        """
        Close MongoDB connection gracefully.
        
        This should be called during application shutdown (e.g., FastAPI lifespan).
        """
        await MongoDB.close()

    @classmethod
    async def generate_chat_name(
        cls,
        *,
        query: str,
        turns_between_chat_name: int = 20,
        max_chat_name_length: int = 50,
        max_chat_name_words: int = 5,
        session_id: str | None = None,
        user_id: str | None = None,
        provider_name: str | None = None,
    ) -> str:
        """
        Generate a meaningful, concise chat name based on a query and optional session context.

        - If no session_id: generate from query only.
        - If session_id: fetch summary + recent messages for context (if session exists for user).
        """
        llm_provider = get_llm_provider(provider_name=provider_name or LLM_PROVIDER)

        if not session_id:
            return await llm_provider.generate_chat_name(
                query=query,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        session = await Session.get_by_id(session_id=session_id, user_id=user_id)
        if session is None:
            return await llm_provider.generate_chat_name(
                query=query,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        chat_name_context_max_messages = 2 * turns_between_chat_name
        summary_task = Summary.get_latest_by_session(session_id=session_id)
        messages_task = Message.get_paginated_by_session(
            session_id=session_id,
            page=1,
            page_size=chat_name_context_max_messages,
        )
        summary, messages = await asyncio.gather(summary_task, messages_task)

        conversation_to_summarize = Message.to_dtos(messages) if messages else None
        return await llm_provider.generate_chat_name(
            query=query,
            previous_summary=summary,
            conversation_to_summarize=conversation_to_summarize,
            max_chat_name_length=max_chat_name_length,
            max_chat_name_words=max_chat_name_words,
        )

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="fetch_user_or_session",
        capture_input=False,
        capture_output=False
    )
    async def _fetch_user_or_session(self) -> None:
        """
        Fetch user or session based on new_user and new_chat flags.
        
        - new_user=False, new_chat=True  -> Fetch user only
        - new_user=False, new_chat=False -> Fetch session only
        - new_user=True -> Do nothing (new user, no data to fetch)
        """
        if self.state.new_user:
            # New user - nothing to fetch
            return
        
        if self.state.new_chat:
            # Existing user, new chat - fetch user only
            self.user = await User.get_by_id_or_cookie(self.user_id, self.user_cookie)
            if not self.user:
                raise UserNotFoundError(
                    "User not found for provided identifiers",
                    details=f"user_id={self.user_id}, user_cookie={self.user_cookie}"
                )
        else:
            # Existing user, existing chat - fetch session only
            if self.session_id:
                if self.user_id:
                    # Primary: use user_id for direct query
                    self.session = await Session.get_by_id(self.session_id, self.user_id)
                elif self.user_cookie:
                    # Fallback: use cookie_id with aggregation lookup
                    self.session = await Session.get_by_id_and_cookie(self.session_id, self.user_cookie)
            if not self.session:
                raise SessionNotFoundError(
                    f"Session not found for session_id: {self.session_id}",
                    details=f"session_id={self.session_id}, user_id={self.user_id}, user_cookie={self.user_cookie}"
                )

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="fetch_context",
        capture_input=False,
        capture_output=False
    )
    async def _fetch_context(self) -> Tuple[List[Message], Summary | None]:
        """
        Fetch the latest N turns (as messages) and the latest summary in parallel.
        
        Returns:
            Tuple of (messages, summary) where messages is a list of Message objects
            from the latest turns and summary is the latest Summary or None.
        
        Traced as DATABASE span for database fetch operations.
        """
        if self.state.new_chat or not self.session_id:
            return [], None
        
        messages_task = Message.get_latest_by_session(
            session_id=str(self.session_id),
            current_turn_number=self.state.turn_number,
            max_turns=MAX_TURNS_TO_FETCH,
        )
        summary_task = Summary.get_latest_by_session(session_id=str(self.session_id))
        
        messages, summary = await asyncio.gather(messages_task, summary_task)
        return messages, summary

    def _convert_messages_to_dtos(self, messages: List[Message]) -> List[MessageDTO]:
        """
        Convert MongoDB Message documents to MessageDTOs.
        """
        return Message.to_dtos(messages)

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="session_updater",
        capture_input=False,
        capture_output=False
    )
    async def update_user_session(
        self, 
        messages: List[MessageDTO], 
        summary: Summary | None, 
        regenerated_summary: bool,
        on_stream_event: StreamCallback | None = None,
    ) -> List[MessageDTO]:
        """
        Create/update user and session, then insert messages into MongoDB.
        """
        # Case 1: New user and new session - create both atomically
        if not self.session and not self.user:
            self.session = await Session.create_with_user(
                cookie_id=self.user_cookie,
                session_id=self.session_id,
            )
        # Case 2: Existing user, new session - create session for existing user
        elif not self.session and self.user:
            self.session = await Session.create_for_existing_user(
                user=self.user,
                session_id=self.session_id,
            )
        
        # Insert messages for the session
        if self.session:
            turn_number = self.state.turn_number
            try:
                if regenerated_summary:
                    await Summary.create_with_session(
                        session=self.session,
                        summary=summary
                    )
                # Ensure writes happen sequentially to avoid Mongo write conflicts
                await self.session.insert_messages(
                    messages=messages,
                    turn_number=turn_number,
                    previous_summary=summary,
                )
                
            except Exception as e:
                logger.error(f"Failed to insert messages for session {self.session_id}: {str(e)}")
                # If insertion fails, still save user message and error response
                if not messages:
                    return messages
                
                # Create fallback messages with error response
                messages = self.create_fallback_messages(messages[0])
                
                # Stream the error response if callback is provided
                if on_stream_event:
                    await stream_fallback_response(on_stream_event, messages[-1])
                
                await self.session.insert_messages(
                    messages=messages,
                    turn_number=turn_number,
                    previous_summary=summary,
                )

        return messages
