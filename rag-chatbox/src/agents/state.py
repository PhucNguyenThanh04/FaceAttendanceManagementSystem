from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from src.features.chat.schemas import ChatHistoryTurn
from src.tools.base_tool import ToolCitation

@dataclass
class AgentStep:
    thought: str
    action: str                     # tên tool: "vector_search", "database_query", "ask_user"
    action_input: dict[str, Any]    # params truyền vào tool.run(**action_input)
    observation: str                # kết quả tool trả về — Supervisor append vào prompt loop kế tiếp
    citations: list[ToolCitation] = field(default_factory=list)
    used_context: bool = False
    low_confidence: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:

    # ── Input (không đổi trong suốt loop) ──
    user_message: str
    employee_id: str
    user_role: str
    conversation_id: str = ""
    chat_history: list[ChatHistoryTurn] = field(default_factory=list)

    # ── Accumulator (cập nhật mỗi iteration) ──
    steps: list[AgentStep] = field(default_factory=list)

    # ── Output (set khi loop kết thúc) ──
    final_answer: str = ""
    finish_reason: Literal["answer", "ask_user", "max_steps", "error"] = "answer"
    is_done: bool = False

    # ── ask_user payload (nếu finish_reason == "ask_user") ──
    ask_user_payload: dict[str, Any] | None = None

    def add_step(self, step: AgentStep) -> None:
        self.steps.append(step)

    def finish_with_answer(self, answer: str) -> None:
        self.final_answer = answer
        self.finish_reason = "answer"
        self.is_done = True

    def finish_with_ask_user(self, payload: dict[str, Any]) -> None:
        self.final_answer = payload.get("question", "")
        self.ask_user_payload = payload
        self.finish_reason = "ask_user"
        self.is_done = True

    def finish_with_error(self, error_message: str) -> None:
        self.final_answer = error_message
        self.finish_reason = "error"
        self.is_done = True

    def finish_max_steps(self) -> None:
        self.final_answer = (
            "Tôi đã thử nhiều cách nhưng chưa tìm được câu trả lời phù hợp. "
            "Bạn vui lòng đặt lại câu hỏi cụ thể hơn."
        )
        self.finish_reason = "max_steps"
        self.is_done = True

    @property
    def step_count(self) -> int:
        return len(self.steps)
