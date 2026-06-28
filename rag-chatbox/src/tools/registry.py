from __future__ import annotations

import json

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
        Tạo mô tả tất cả tools cho LLM prompt.

        Output dạng:
            Các tool bạn có thể sử dụng:

            1. vector_search: Tìm kiếm thông tin trong tài liệu...
            2. employee_query: Tra cứu hồ sơ nhân viên hiện tại...
               input_schema: {...}
            3. shift_query: Tra cứu ca làm...
        """
        if not self._tools:
            return "Không có tool nào khả dụng."

        lines = ["Các tool bạn có thể sử dụng:", ""]
        for index, tool in enumerate(self._tools.values(), start=1):
            tool_info = tool.to_dict()
            lines.append(f"{index}. {tool_info['name']}: {tool_info['description']}")
            input_schema = tool_info.get("input_schema")
            if input_schema is not None:
                lines.append(
                    "   input_schema: "
                    f"{json.dumps(input_schema, ensure_ascii=False)}"
                )

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
