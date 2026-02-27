"""
Base SessionManager abstract class for OmniAgent.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, List, Tuple
import logging

from omniagent.ai.providers import get_llm_provider
from omniagent.ai.providers.utils import StreamCallback, stream_fallback_response

from omniagent.domain_protocols import MessageProtocol, SessionProtocol, SummaryProtocol, UserProtocol
from omniagent.utils.general import generate_id

from omniagent.config import MAX_TOKEN_THRESHOLD
from omniagent.config import (
    AISDK_ID_LENGTH,
    CHAT_NAME_LLM_API_TYPE,
    CHAT_NAME_LLM_PROVIDER,
    CHAT_NAME_MODEL,
    CHAT_NAME_REQUEST_KWARGS,
    CHAT_NAME_TEMPERATURE,
    MAX_TURNS_TO_FETCH,
)

from omniagent.types.llm import LLMModelConfig
from omniagent.types.state import State
from omniagent.types.message import MessageDTO

from omniagent.tracing import CustomSpanKinds, trace_method
from omniagent.tracing import track_state_change

logger = logging.getLogger(__name__)


class SessionManager(ABC):
    """
    Abstract base class for session management.
    
    Provides common logic for state management and context orchestration.
    Subclasses must implement database-specific methods for fetching and persisting data.
    """

    def __init__(
        self, 
        session_id: str | None, 
        user_client_id: str,
        state: dict | None = None,
    ):
        self.state = self._inititialise_state(state=state or {})
        self.session_id = session_id
        self.user_client_id = user_client_id
        self.user: UserProtocol | None = None
        self.session: SessionProtocol | None = None
        self.new_chat: bool = False
        self.new_user: bool = False

    def _inititialise_state(self, state: dict) -> State:
        return State(user_defined_state=state)

    @classmethod
    @abstractmethod
    def _get_message_model(cls) -> Any:
        """Return backend-specific Message model class."""
        ...

    @classmethod
    @abstractmethod
    def _get_summary_model(cls) -> Any:
        """Return backend-specific Summary model class."""
        ...

    @classmethod
    @abstractmethod
    def _get_session_model(cls) -> Any:
        """Return backend-specific Session model class."""
        ...

    @classmethod
    @abstractmethod
    def _get_user_model(cls) -> Any:
        """Return backend-specific User model class."""
        ...

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
    ) -> str:
        """Generate a chat name using backend-specific context retrieval and provider calls."""
        chat_name_llm_config = LLMModelConfig(
            provider=CHAT_NAME_LLM_PROVIDER,
            api_type=CHAT_NAME_LLM_API_TYPE,
            model=CHAT_NAME_MODEL,
            temperature=CHAT_NAME_TEMPERATURE,
            request_kwargs=CHAT_NAME_REQUEST_KWARGS,
        )
        llm_provider = get_llm_provider(
            provider_name=chat_name_llm_config.provider,
            api_type=chat_name_llm_config.api_type,
        )

        if not session_id or not client_id:
            return await llm_provider.generate_chat_name(
                query=query,
                llm_config=chat_name_llm_config,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        session_model = cls._get_session_model()
        session = await session_model.get_by_id_and_client_id(
            session_id=session_id,
            client_id=client_id,
        )
        if session is None:
            return await llm_provider.generate_chat_name(
                query=query,
                llm_config=chat_name_llm_config,
                max_chat_name_length=max_chat_name_length,
                max_chat_name_words=max_chat_name_words,
            )

        message_model = cls._get_message_model()
        summary_model = cls._get_summary_model()
        chat_name_context_max_messages = 2 * turns_between_chat_name
        summary_task = summary_model.get_latest_by_session(session_id=session_id)
        messages_task = message_model.get_paginated_by_session(
            session_id=session_id,
            page=1,
            page_size=chat_name_context_max_messages,
        )
        summary, messages = await asyncio.gather(summary_task, messages_task)

        conversation_to_summarize = message_model.to_dtos(messages) if messages else None
        return await llm_provider.generate_chat_name(
            query=query,
            llm_config=chat_name_llm_config,
            previous_summary=summary,
            conversation_to_summarize=conversation_to_summarize,
            max_chat_name_length=max_chat_name_length,
            max_chat_name_words=max_chat_name_words,
        )

    async def get_latest_summary_for_fallback(self) -> SummaryProtocol | None:
        """Return latest persisted summary for fallback/error handling paths."""
        if not self.session:
            return None
        summary_model = self._get_summary_model()
        return await summary_model.get_latest_by_session(session_id=str(self.session.id))

    async def _empty_session(self) -> None:
        return None

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="fetch_user_or_session",
        capture_input=False,
        capture_output=False,
    )
    async def _fetch_user_or_session(self) -> None:
        """Fetch/create user and session using backend-specific models."""
        user_model = self._get_user_model()
        session_model = self._get_session_model()
        user_task = user_model.get_by_client_id(self.user_client_id)
        session_task = (
            session_model.get_by_id_and_client_id(self.session_id, self.user_client_id)
            if self.session_id
            else self._empty_session()
        )
        self.user, self.session = await asyncio.gather(user_task, session_task)

        if not self.user:
            self.new_user = True
            self.new_chat = True
            self.session = await session_model.create_with_user(
                client_id=self.user_client_id,
                session_id=self.session_id,
            )
            return

        if not self.session:
            self.new_chat = True
            self.session = await session_model.create_for_existing_user(
                user=self.user,
                session_id=self.session_id,
            )

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="fetch_context",
        capture_input=False,
        capture_output=False,
    )
    async def _fetch_context(self) -> Tuple[List[MessageProtocol], SummaryProtocol | None]:
        """Fetch latest messages and summary for the active session."""
        if self.new_chat or not self.session_id:
            return [], None

        message_model = self._get_message_model()
        summary_model = self._get_summary_model()
        messages_task = message_model.get_latest_by_session(
            session_id=str(self.session_id),
            current_turn_number=self.state.turn_number,
            max_turns=MAX_TURNS_TO_FETCH,
        )
        summary_task = summary_model.get_latest_by_session(session_id=str(self.session_id))
        messages, summary = await asyncio.gather(messages_task, summary_task)
        return messages, summary

    def _convert_messages_to_dtos(self, messages: List[MessageProtocol]) -> List[MessageDTO]:
        """Convert backend messages to MessageDTO."""
        message_model = self._get_message_model()
        return message_model.to_dtos(messages)

    @trace_method(
        kind=CustomSpanKinds.DATABASE.value,
        graph_node_id="session_updater",
        capture_input=False,
        capture_output=False,
    )
    async def update_user_session(
        self,
        messages: List[MessageDTO],
        summary: SummaryProtocol | None,
        regenerated_summary: bool,
        on_stream_event: StreamCallback | None = None,
    ) -> List[MessageDTO]:
        """Persist messages and optional regenerated summary for current session."""
        if not self.session:
            return messages

        turn_number = self.state.turn_number
        try:
            persisted_summary = summary
            if regenerated_summary and summary is not None:
                summary_model = self._get_summary_model()
                persisted_summary = await summary_model.create_with_session_id(
                    session_id=str(self.session.id),
                    summary=summary,
                )

            await self.session.insert_messages(
                messages=messages,
                turn_number=turn_number,
                previous_summary=persisted_summary,
            )
        except Exception as exc:
            logger.error(f"Failed to insert messages for session {self.session_id}: {exc}")
            if not messages:
                return messages

            messages = self.create_fallback_messages(messages[0])
            if on_stream_event:
                await stream_fallback_response(on_stream_event, messages[-1])

            await self.session.insert_messages(
                messages=messages,
                turn_number=turn_number,
                previous_summary=summary,
            )

        return messages

    def update_state(self, **kwargs) -> None:
        """
        Update state with provided key-value pairs.
        
        Automatically tracks state changes in the current span for observability.
        
        Args:
            **kwargs: Key-value pairs to update in state.
        """
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                old_value = getattr(self.state, key)
                setattr(self.state, key, value)
                
                # Track state change in current span
                track_state_change(key, old_value, value)

    async def get_context_and_update_state(self) -> Tuple[List[MessageDTO], SummaryProtocol | None]:
        """
        Fetch context (messages + summary) and user/session in parallel, then update state.
        
        Algorithm:
        1. Fetch messages from latest turns and calculate tokens after summary
        2. If tokens < MAX_TOKEN_THRESHOLD, include additional older messages until threshold met
        3. Update state with turns_after_last_summary, total_token_after_last_summary, active_summary
        4. Return messages in chronological order with summary
        
        Returns:
            Tuple of (messages, summary) - messages from selected turns in order of arrival.
        """
        # Fetch context and user/session in parallel
        context_task = self._fetch_context()
        user_or_session_task = self._fetch_user_or_session()
        (all_messages, summary), _ = await asyncio.gather(context_task, user_or_session_task)
        if self.session:
            self.update_state(turn_number=self.session.latest_turn_number+1)
        
        if not all_messages:
            return [], summary
        
        # Messages are already in chronological order from get_latest_by_session
        
        # Determine the start point based on summary
        end_turn_number = summary.end_turn_number if summary else 0
        
        # Step 1: Get messages after summary (end_turn_number + 1 to current)
        messages_after_summary = [m for m in all_messages if m.turn_number > end_turn_number]
        
        # Count unique turns after summary
        turns_after_summary = {m.turn_number for m in messages_after_summary}
        turns_after_last_summary = len(turns_after_summary)
        total_token_after_last_summary = sum(m.token_count for m in messages_after_summary)
        
        # Step 2: Collect context messages - start with messages after summary
        context_messages = messages_after_summary.copy()
        
        # Step 3 & 4: If tokens < threshold, fetch additional older messages
        if total_token_after_last_summary < MAX_TOKEN_THRESHOLD:
            # Get messages at or before end_turn_number (older messages)
            older_messages = [m for m in all_messages if m.turn_number <= end_turn_number]
            # Reverse to process from most recent to oldest
            older_messages.reverse()
            
            for message in older_messages:
                total_token_after_last_summary += message.token_count
                context_messages.insert(0, message)  # Insert at beginning to maintain order
                if total_token_after_last_summary >= MAX_TOKEN_THRESHOLD:
                    break
        
        # Update state
        self.update_state(
            turns_after_last_summary=turns_after_last_summary,
            total_token_after_last_summary=total_token_after_last_summary,
            active_summary=summary
        )
        
        # Convert Message documents to MessageDTOs (implemented by subclass)
        message_dtos = self._convert_messages_to_dtos(context_messages)
        
        return message_dtos, summary
    
    def create_fallback_messages(self, user_query_dto: MessageDTO) -> List[MessageDTO]:
        """
        Create fallback messages with user query and error response.
        
        Args:
            user_query_dto: The original user query message
            
        Returns:
            List containing user query and error response message
        """
        # Create error response DTO using new schema
        error_message_dto = MessageDTO.create_ai_message(
            message_id=generate_id(AISDK_ID_LENGTH, "nanoid"),
            metadata={"error": True}
        ).update_ai_text_message(
            text="I apologize, but something went wrong while processing your request. Please try again."
        )
        
        # Return list with user message and error response
        return [user_query_dto, error_message_dto]
