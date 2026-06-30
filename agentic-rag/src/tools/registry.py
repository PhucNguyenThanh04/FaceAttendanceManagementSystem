from __future__ import annotations

from src.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Quản lý danh sách tools cho Supervisor.

    Mỗi request tạo 1 registry riêng vì một số tool cần context
    per-request (allowed_role, employee_id).

    Usage:
        registry = ToolRegistry()
        registry.register(VectorSearchTool(...))
        registry.register(EmployeeQueryTool(...))
        registry.register(ShiftQueryTool(...))
        registry.register(AttendanceQueryTool(...))
        registry.register(AskUserTool())

        tool = registry.get("vector_search")
        await tool.run(query="...")
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' đã được đăng ký. "
                f"Mỗi tool name phải là duy nhất."
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools)) or "(không có tool nào)"
            raise KeyError(
                f"Tool '{name}' không tồn tại. "
                f"Các tool có sẵn: {available}"
            )
        return tool

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def build_tools_prompt(self) -> str:
        """
        Tạo mô tả compact cho LLM prompt.

        Không dump toàn bộ JSON schema để tránh model nhỏ sinh nhầm field.
        """
        if not self._tools:
            return "Không có tool nào khả dụng."

        lines = ["TOOLS:"]
        for tool in self._tools.values():
            lines.append(
                "- "
                f"{tool.name}: {self._compact_usage(tool)} "
                f"Input: {self._input_example(tool.name)}"
            )

        return "\n".join(lines)

    @staticmethod
    def _compact_usage(tool: BaseTool) -> str:
        usage_by_name = {
            "employee_query": "Tra cứu hồ sơ nhân viên hiện tại.",
            "shift_query": "Tra cứu ca làm hoặc lịch làm việc.",
            "attendance_query": "Tra cứu chấm công, check-in/out, đi trễ/về sớm.",
            "vector_search": "Tìm nội quy, chính sách, quy định trong tài liệu.",
            "ask_user": "Hỏi thêm khi thiếu thông tin mà tool không tự lấy được.",
        }
        return usage_by_name.get(tool.name, tool.description)

    @staticmethod
    def _input_example(tool_name: str) -> str:
        examples = {
            "employee_query": "{}",
            "shift_query": '{"as_of":"YYYY-MM-DD"} hoặc {}',
            "attendance_query": (
                '{"event_type":"check_in|check_out|unknown",'
                '"accepted":true,'
                '"event_time_from":"ISO datetime",'
                '"event_time_to":"ISO datetime"} hoặc {}'
            ),
            "vector_search": '{"query":"câu hỏi ngắn"}',
            "ask_user": (
                '{"question":"câu hỏi",'
                '"options":[],'
                '"allow_free_text":true}'
            ),
        }
        return examples.get(tool_name, "{}")

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
