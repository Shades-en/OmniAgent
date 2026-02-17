"""
MongoDB-specific SessionManager implementation using Beanie ODM.
"""

import asyncio
from typing import List, Tuple

import logging

from omniagent.session.base import SessionManager
from omniagent.ai.providers import get_llm_provider
from omniagent.types.message import MessageDTO
from omniagent.db.document_models import DocumentModels, get_message_model, get_summary_model
from omniagent.schemas.mongo import User, Session, Summary
from omniagent.protocols import MessageProtocol
from omniagent.config import MAX_TURNS_TO_FETCH, LLM_PROVIDER
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
        models: DocumentModels | None = None,
        extra_document_models=None,
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
            models=models,
            extra_document_models=extra_document_models,
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
        client_id: str | None = None,
        provider_name: str | None = None,
        provider_options: dict | None = None,
    ) -> str:
        """
        Generate a meaningful, concise chat name based on a query and optional session context.

        - If no session_id: generate from query only.
        - If session_id: fetch summary + recent messages for context (if session exists for user).
        """
        # Extract api_type from provider_options if available (for OpenAI)
        # Other providers can use different keys from provider_options
        llm_provider = get_llm_provider(
            provider_name=provider_name or LLM_PROVIDER,
            **(provider_options or {})
        )

        if not session_id:
            return await llm_provider.generate_chat_name(
                query=query,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        session = await Session.get_by_id_and_client_id(session_id=session_id, client_id=client_id) if client_id else None
        if session is None:
            return await llm_provider.generate_chat_name(
                query=query,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        MessageModel = get_message_model()
        SummaryModel = get_summary_model()

        chat_name_context_max_messages = 2 * turns_between_chat_name
        summary_task = SummaryModel.get_latest_by_session(session_id=session_id)
        messages_task = MessageModel.get_paginated_by_session(
            session_id=session_id,
            page=1,
            page_size=chat_name_context_max_messages,
        )
        summary, messages = await asyncio.gather(summary_task, messages_task)

        conversation_to_summarize = MessageModel.to_dtos(messages) if messages else None
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
        Fetch user and session in parallel based on client_id and session_id.
        
        Sets instance variables:
        - self.new_user = True if user not found
        - self.new_chat = True if session not found (or new user)
        - self.user and self.session populated if found or created
        
        If user not found: creates user + session atomically.
        If user found but session not found: creates session for existing user.
        """
        # Fetch user and session in parallel
        user_task = User.get_by_client_id(self.user_client_id)
        session_task = (
            Session.get_by_id_and_client_id(self.session_id, self.user_client_id)
            if self.session_id
            else asyncio.coroutine(lambda: None)()
        )
        
        self.user, self.session = await asyncio.gather(user_task, session_task)
        
        # Case 1: User not found - create user + session atomically
        if not self.user:
            self.new_user = True
            self.new_chat = True
            self.session = await Session.create_with_user(
                client_id=self.user_client_id,
                session_id=self.session_id,
            )
            return
        
        # Case 2: User found but session not found - create session for existing user
        if not self.session:
            self.new_chat = True
            self.session = await Session.create_for_existing_user(
                user=self.user,
                session_id=self.session_id,
            )

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="fetch_context",
        capture_input=False,
        capture_output=False
    )
    async def _fetch_context(self) -> Tuple[List[MessageProtocol], Summary | None]:
        """
        Fetch the latest N turns (as messages) and the latest summary in parallel.
        
        Returns:
            Tuple of (messages, summary) where messages is a list of Message objects
            from the latest turns and summary is the latest Summary or None.
        
        Traced as DATABASE span for database fetch operations.
        """
        if self.new_chat or not self.session_id:
            return [], None
        
        MessageModel = get_message_model()
        SummaryModel = get_summary_model()

        messages_task = MessageModel.get_latest_by_session(
            session_id=str(self.session_id),
            current_turn_number=self.state.turn_number,
            max_turns=MAX_TURNS_TO_FETCH,
        )
        summary_task = SummaryModel.get_latest_by_session(session_id=str(self.session_id))
        
        messages, summary = await asyncio.gather(messages_task, summary_task)
        return messages, summary

    def _convert_messages_to_dtos(self, messages: List[MessageProtocol]) -> List[MessageDTO]:
        """
        Convert MongoDB Message documents to MessageDTOs.
        """
        MessageModel = get_message_model()
        return MessageModel.to_dtos(messages)

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
        Insert messages into MongoDB for the current session.
        
        Note: User and session creation is now handled in _fetch_user_or_session,
        so self.session is guaranteed to exist at this point.
        """
        # Insert messages for the session
        if self.session:
            turn_number = self.state.turn_number
            try:
                if regenerated_summary:
                    SummaryModel = get_summary_model()
                    await SummaryModel.create_with_session(
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
