from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str
    description: str  # LLM đọc cái này để biết chọn tool nào

    @abstractmethod
    async def run(self, **kwargs) -> str:
        """
        Thực thi tool và trả về kết quả dạng string.
        Agent sẽ đọc string này làm Observation.
        """
        pass

    def to_dict(self) -> dict:
        """Mô tả tool cho LLM đọc trong prompt."""
        return {
            "name": self.name,
            "description": self.description,
        }