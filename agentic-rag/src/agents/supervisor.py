from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from src.agents.executor import Executor
from src.agents.pending_store import AgentPendingStore
from src.agents.state import AgentState, AgentStep
from src.core.settings import get_settings
from src.features.chat.schemas import ChatRequest
from src.integrations.llm.client import GeminiClient, LLMError
from src.integrations.llm.prompts import PromptBuilder
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

MAX_ASK_USER_COUNT = 2


class Supervisor:
    """
    Coordinates the ReAct loop for one chat request.

    Supervisor owns state and loop control. The caller owns tool composition.
    Executor owns tool execution details.
    """

    def __init__(
        self,
        llm_client: GeminiClient,
        pending_store: AgentPendingStore | None = None,
        max_steps: int | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        settings = get_settings() if max_steps is None or prompt_builder is None else None
        self.llm_client = llm_client
        self.pending_store = pending_store
        self.max_steps = max_steps if max_steps is not None else settings.agent_max_steps
        self.prompt_builder = (
            prompt_builder
            if prompt_builder is not None
            else PromptBuilder.from_settings(settings)
        )

    async def run(
        self,
        request: ChatRequest,
        registry: ToolRegistry,
    ) -> AgentState:
        state = await self._build_initial_state(request)

        executor = Executor(registry)
        system_prompt = PromptBuilder.build_system_prompt(
            tool_descriptions=registry.build_tools_prompt(),
            current_date=date.today().isoformat(),
        )

        logger.info(
            "Supervisor started | employee_id=%s user_role=%s chat_history_count=%d message=%s",
            request.employee_id,
            request.user_role,
            len(request.chat_history),
            request.message[:80],
        )

        while not state.is_done and state.step_count < self.max_steps:
            try:
                parsed = await self._call_llm(state, system_prompt)
            except (LLMError, json.JSONDecodeError, ValueError) as exc:
                logger.error("LLM error in supervisor loop: %s", exc)
                state.finish_with_error(
                    "Xin lỗi, tôi gặp lỗi khi xử lý yêu cầu. "
                    "Bạn vui lòng thử lại."
                )
                break

            thought = str(parsed.get("thought", ""))
            action = str(parsed.get("action", ""))
            action_input = parsed.get("action_input", {})
            if not isinstance(action_input, dict):
                logger.warning(
                    "Invalid action_input type from LLM | action=%s type=%s",
                    action,
                    type(action_input).__name__,
                )
                action_input = {}

            if action == "ask_user" and self._ask_user_count(state) >= MAX_ASK_USER_COUNT:
                logger.warning(
                    "Max ask_user count reached | conversation_id=%s count=%d",
                    request.conversation_id,
                    self._ask_user_count(state),
                )
                state.finish_with_error("Không đủ thông tin để trả lời.")
                break

            if action == "final_answer":
                state.add_step(
                    AgentStep(
                        thought=thought,
                        action=action,
                        action_input=action_input,
                        observation="",
                    )
                )
                self._log_step(state, state.steps[-1])
                answer = str(action_input.get("answer") or thought or "")
                if not action_input.get("answer"):
                    logger.warning("final_answer action missing answer field")
                state.finish_with_answer(answer)
                break

            result = await executor.execute(action, action_input)
            state.add_step(
                AgentStep(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=result.observation,
                    is_error=result.is_error,
                    citations=result.citations,
                    used_context=result.used_context,
                    low_confidence=result.low_confidence,
                    metadata=result.metadata,
                )
            )
            self._log_step(state, state.steps[-1])

            if result.is_ask_user:
                state.finish_with_ask_user(result.ask_user_payload or {})
                break

        if not state.is_done:
            state.finish_max_steps()
            logger.warning(
                "Supervisor max steps reached | employee_id=%s actions=%s message=%s",
                request.employee_id,
                [step.action for step in state.steps],
                request.message[:80],
            )

        await self._sync_pending_state(request.conversation_id, state)

        logger.info(
            "Supervisor finished | reason=%s steps=%d",
            state.finish_reason,
            state.step_count,
        )
        return state

    async def _build_initial_state(self, request: ChatRequest) -> AgentState:
        if self.pending_store is not None:
            pending = await self.pending_store.get_pending(request.conversation_id)
            if pending is not None:
                try:
                    if (
                        str(pending.get("employee_id")) != request.employee_id
                        or str(pending.get("user_role")) != request.user_role
                    ):
                        logger.warning(
                            "Pending state context mismatch | conversation_id=%s",
                            request.conversation_id,
                        )
                        await self.pending_store.delete_pending(request.conversation_id)
                    else:
                        state = AgentState.from_pending_dict(pending)
                        state.resume_from_ask_user_answer(request.message)
                        logger.info(
                            "Supervisor resumed pending state | conversation_id=%s steps=%d",
                            request.conversation_id,
                            state.step_count,
                        )
                        return state
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning(
                        "Invalid pending state, starting a new loop | "
                        "conversation_id=%s error=%s",
                        request.conversation_id,
                        exc,
                    )
                    await self.pending_store.delete_pending(request.conversation_id)

        return AgentState(
            user_message=request.message,
            employee_id=request.employee_id,
            user_role=request.user_role,
            chat_history=list(request.chat_history),
        )

    async def _sync_pending_state(
        self,
        conversation_id: str,
        state: AgentState,
    ) -> None:
        if self.pending_store is None:
            return

        if state.finish_reason == "ask_user":
            try:
                await self.pending_store.save_pending(
                    conversation_id,
                    state.to_pending_dict(),
                )
            except Exception as exc:
                logger.error(
                    "Failed to save agent pending state: conversation_id=%s error=%s",
                    conversation_id,
                    exc,
                    exc_info=True,
                )
                await self.pending_store.delete_pending(conversation_id)
                state.finish_with_error(
                    "Xin lỗi, tôi chưa thể lưu trạng thái cần hỏi thêm. "
                    "Bạn vui lòng thử lại."
                )
            return

        await self.pending_store.delete_pending(conversation_id)

    @staticmethod
    def _ask_user_count(state: AgentState) -> int:
        return sum(1 for step in state.steps if step.action == "ask_user")

    async def _call_llm(
        self,
        state: AgentState,
        system_prompt: str,
    ) -> dict[str, Any]:
        scratchpad = self.prompt_builder.build_scratchpad(state.steps)
        user_prompt = self.prompt_builder.build_react_prompt(
            user_message=state.user_message,
            chat_history=state.chat_history,
            scratchpad=scratchpad,
        )

        response = await self.llm_client.generate_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )
        parsed = json.loads(response.content)

        if not isinstance(parsed, dict):
            raise ValueError(f"Gemini response must be a JSON object: {parsed}")
        if "action" not in parsed:
            raise ValueError(f"Gemini response thiếu field 'action': {parsed}")

        return parsed

    @staticmethod
    def _log_step(state: AgentState, step: AgentStep) -> None:
        logger.info(
            "Supervisor step | step=%d action=%s is_error=%s "
            "used_context=%s low_confidence=%s observation_length=%d",
            state.step_count,
            step.action,
            step.is_error,
            step.used_context,
            step.low_confidence,
            len(step.observation or ""),
        )
