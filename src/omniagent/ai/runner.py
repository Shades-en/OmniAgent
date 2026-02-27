from __future__ import annotations

from opentelemetry.trace import SpanKind

from omniagent import config
from omniagent.ai.agents.agent import Agent
from omniagent.ai.providers.llm_provider import StreamCallback
from omniagent.types.chat import MessageQuery, RunnerOptions
from omniagent.exceptions import (
    SessionNotFoundError,
    UserNotFoundError,
    MessageRetrievalError,
    MaxStepsReachedError,
)
from omniagent.domain_protocols import SummaryProtocol
from omniagent.types.message import MessageDTO
from omniagent.session import SessionManager
from omniagent.tracing import trace_method
from omniagent.utils.general import generate_id
from omniagent.config import AISDK_ID_LENGTH
from omniagent.ai.providers.utils import stream_fallback_response, dispatch_stream_event, create_finish_event
from omniagent.utils.task_registry import register_task, unregister_task
from omniagent.utils.streaming import format_sse_event, format_sse_done
from omniagent.constants import STREAM_EVENT_DATA_SESSION, STREAM_EVENT_ERROR

import asyncio
from typing import List, AsyncGenerator, Tuple
from dataclasses import dataclass

from openinference.semconv.trace import OpenInferenceSpanKindValues
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result of handling a query with messages, summary, and fallback status."""
    messages: List[MessageDTO]
    summary: SummaryProtocol | None
    fallback: bool
    regenerated_summary: bool

class Runner:
    def __init__(self, agent: Agent, session_manager: SessionManager, options: RunnerOptions | None = None) -> None:
        self.agent = agent
        self.session_manager = session_manager
        self.options = options or RunnerOptions()

    @trace_method(
        kind=SpanKind.INTERNAL,
        graph_node_id="llm_parallel_generation",
        capture_input=False,
        capture_output=False
    )
    async def _generate_response_and_metadata(
        self,
        conversation_history: List[MessageDTO],
        previous_conversation: List[MessageDTO],
        ai_message: MessageDTO,
        summary: SummaryProtocol | None,
        query: str,
        tool_call: bool,
        on_stream_event: StreamCallback | None = None,
    ) -> tuple[bool, SummaryProtocol | None]:
        """
        Generate LLM response and summary in parallel.
        
        Runs two LLM operations concurrently:
        1. Generate response (with potential tool calls)
        2. Generate summary (based on context)
        
        Args:
            conversation_history: Full conversation including system message and user query
            previous_conversation: Previous turns (for summarization)
            summary: Current summary (if any)
            query: User's query
            tool_call: Whether this is a tool call iteration
            on_stream_event: Callback for streaming events
            
        Returns:
            Tuple of (tool_call, new_summary)
        
        Traced as INTERNAL span for parallel LLM operations.
        """
        # Use mock methods if MOCK_AI_RESPONSE is enabled
        if config.MOCK_AI_RESPONSE:
            return await asyncio.gather(
                self.agent.llm_provider.mock_generate_response(step=self.session_manager.state.step),
                self.agent.llm_provider.mock_generate_summary(
                    query=query,
                    turns_after_last_summary=self.session_manager.state.turns_after_last_summary,
                    turn_number=self.session_manager.state.turn_number
                ),
            )
        
        # Use real LLM methods - stream only if options.stream is True AND callback provided
        stream_enabled = self.options.stream and on_stream_event is not None
        return await asyncio.gather(
            self.agent.llm_provider.generate_response(
                conversation_history=conversation_history,
                llm_config=self.agent.model,
                tools=self.agent.tools,
                ai_message=ai_message,
                stream=stream_enabled,
                on_stream_event=on_stream_event if stream_enabled else None,
            ),
            self.agent.llm_provider.generate_summary(
                conversation_to_summarize=previous_conversation,
                previous_summary=summary,
                query=query,
                llm_config=self.agent.model.effective_summary_config(),
                turns_after_last_summary=self.session_manager.state.turns_after_last_summary,
                context_token_count=self.session_manager.state.total_token_after_last_summary,
                tool_call=tool_call,
                new_chat=self.session_manager.new_chat,
                turn_number=self.session_manager.state.turn_number
            ),
        )

    @trace_method(
        kind=OpenInferenceSpanKindValues.CHAIN,
        capture_output=False,
        graph_node_id="query_handler"
    )
    async def _handle_query(
        self,
        query_message: MessageQuery,
        on_stream_event: StreamCallback | None = None,
    ) -> QueryResult:
        turn_completed = False
        tool_call = False
        query = query_message.query
        query_id = query_message.id

        conversation_history: List[MessageDTO] = []
        previous_conversation: List[MessageDTO] = []
        summary: SummaryProtocol | None = None
        new_summary: SummaryProtocol | None = None

        user_query_message = MessageDTO.create_human_message(text=query, message_id=query_id)
        message_id = generate_id(AISDK_ID_LENGTH, "nanoid")
        ai_message = MessageDTO.create_ai_message(message_id=message_id)

        try:
            while not turn_completed:
                if not tool_call:
                    previous_conversation, summary = await self.session_manager.get_context_and_update_state()
                    system_message = self.agent.llm_provider.build_system_message(
                        instructions=self.agent.instructions,
                        summary=summary.content if summary else None,
                    )
                    conversation_history = [system_message] + previous_conversation
                    conversation_history.append(user_query_message)

                # Generate LLM response and summary in parallel
                tool_call, returned_summary = await self._generate_response_and_metadata(
                    conversation_history=conversation_history, # for LLM response, contains user message and tool call if happened
                    previous_conversation=previous_conversation, # for summary does not contain recent tool call
                    ai_message=ai_message,
                    summary=summary,
                    query=query,
                    tool_call=tool_call, # for summary
                    on_stream_event=on_stream_event
                )
                
                # Only update summary if not None (which happens when tool calls override in second iteration)
                if returned_summary is not None:
                    new_summary = returned_summary

                # If tool call is not made then turn is completed. If tool call is made 
                # then turn will be completed once AI executes the tool call, in the next iteration.
                if tool_call:
                    conversation_history.append(ai_message)
                else:
                    turn_completed = True
                
                if not turn_completed:
                    self.session_manager.update_state(step=self.session_manager.state.step+1)
                    if self.session_manager.state.step > config.MAX_STEPS:
                        raise MaxStepsReachedError(
                            "Agent exceeded maximum number of steps allowed",
                            details="The agent made too many tool calls in a single turn. Consider simplifying the task or increasing MAX_STEPS.",
                            current_step=self.session_manager.state.step,
                            max_steps=config.MAX_STEPS
                        )
                # If new summary is generated it means that the current turn's previous conversation is now the new summary
                # This is because new summary encapsulates all information from the previous conversation except the current turn
                
                turn_previous_summary = summary
                regenerated_summary = False
                if new_summary:
                    turn_previous_summary = new_summary
                    regenerated_summary = True

            return QueryResult(
                messages=[user_query_message, ai_message],
                summary=turn_previous_summary,
                fallback=False,
                regenerated_summary=regenerated_summary
            )
        except asyncio.CancelledError:
            # User cancelled the stream - save partial content that was accumulated
            logger.info("Query cancelled by user, saving partial content")
            # ai_message already contains partial content accumulated during streaming
            # Return it so it can be saved to DB
            return QueryResult(
                messages=[user_query_message, ai_message],
                summary=summary,  # Use existing summary, don't wait for new one
                fallback=False,
                regenerated_summary=False
            )
        except (SessionNotFoundError, UserNotFoundError, MessageRetrievalError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error in _handle_query: {e}")
            fallback_messages = self.session_manager.create_fallback_messages(user_query_message)
            if on_stream_event and fallback_messages:
                await stream_fallback_response(on_stream_event, fallback_messages[-1])
            
            # Try to get summary: use existing, fetch from DB, or None
            previous_summary = summary
            if not previous_summary and self.session_manager.session:
                previous_summary = await self.session_manager.get_latest_summary_for_fallback()
            
            return QueryResult(
                messages=fallback_messages,
                summary=previous_summary,
                fallback=True,
                regenerated_summary=False
            )

    @trace_method(
        kind=OpenInferenceSpanKindValues.AGENT,
        graph_node_id=lambda self: self.agent.name.lower()
    )
    async def _run_with_optional_stream(
        self,
        query_message: MessageQuery,
        on_stream_event: StreamCallback | None = None,
    ) -> dict:
        stream_enabled = self.options.stream and on_stream_event is not None
        stream_callback = on_stream_event if stream_enabled else None
        session_id = self.session_manager.session_id
        
        # Register task for cancellation when streaming is enabled
        if stream_enabled and session_id:
            current_task = asyncio.current_task()
            if current_task:
                register_task(session_id, current_task)
        
        try:
            result: QueryResult = await self._handle_query(query_message, stream_callback)
            # Shield update_user_session from task cancellation to ensure DB writes complete
            messages = await asyncio.shield(self.session_manager.update_user_session(
                messages=result.messages,
                summary=result.summary,
                regenerated_summary=result.regenerated_summary,
                on_stream_event=stream_callback,
            ))
            
            # Send finish event after DB writes complete
            if stream_enabled:
                await dispatch_stream_event(stream_callback, create_finish_event("stop"))
            
            return {
                "messages": [
                    msg.model_dump(mode='json', exclude={"session", "previous_summary"})
                    for msg in messages
                ],
                "summary": (
                    result.summary.model_dump(mode='json', exclude={"session"})
                    if result.summary
                    else None
                ),
                "session_id": str(self.session_manager.session.id)
            }
        finally:
            # Unregister task when done (success or failure)
            if stream_enabled and session_id:
                unregister_task(session_id)

    async def run(
        self,
        query_message: MessageQuery,
    ) -> dict:
        """Run agent in non-streaming mode."""
        return await self._run_with_optional_stream(query_message=query_message)

    async def run_stream(
        self,
        query_message: MessageQuery,
    ) -> Tuple[AsyncGenerator[str, None], asyncio.Future]:
        """
        Run the agent with streaming, returning a generator and result future.
        
        This method provides a cleaner streaming API where:
        - The generator yields formatted SSE events (including DONE sentinel)
        - The result dict is available via the future after stream completes
        
        Args:
            query_message: The user's query message
            
        Returns:
            Tuple of (event_generator, result_future):
            - event_generator: AsyncGenerator yielding formatted SSE strings
            - result_future: Future that resolves to the result dict after completion
        """
        queue: asyncio.Queue = asyncio.Queue()
        result_future: asyncio.Future = asyncio.get_event_loop().create_future()
        
        async def stream_callback(event):
            await queue.put(event)
        
        async def run_chat():
            try:
                result = await self._run_with_optional_stream(
                    query_message=query_message,
                    on_stream_event=stream_callback,
                )
                # Send data-session event with result
                await queue.put({"type": STREAM_EVENT_DATA_SESSION, "data": result})
                result_future.set_result(result)
            except asyncio.CancelledError:
                await queue.put({"type": "cancelled", "message": "Stream cancelled by user"})
                result_future.set_exception(asyncio.CancelledError())
            except Exception as exc:
                await queue.put({"type": STREAM_EVENT_ERROR, "errorText": str(exc)})
                result_future.set_exception(exc)
            finally:
                await queue.put(None)  # Signal end of stream
        
        # Start the chat task
        asyncio.create_task(run_chat())
        
        async def event_generator() -> AsyncGenerator[str, None]:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield format_sse_event(event)
            yield format_sse_done()
        
        return event_generator(), result_future
