import asyncio
from typing import Any

from app.core.config import settings


class LlamaParseClientService:
    def __init__(self, client):
        self.client = client

    async def parse_file(self, file_path: str) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            file_obj = await self.client.files.create(file=f, purpose="parse")

        job_result = await self.client.parsing.parse(
            file_id=file_obj.id,
            tier="agentic",
            version="latest",
            expand=["markdown_full", "text_full", "items"],
        )

        job_id = job_result.job.id

        while True:
            result = await self.client.parsing.get(
                job_id=job_id,
                expand=["markdown_full", "text_full", "items"],
            )

            status = getattr(getattr(result, "job", None), "status", None)

            if getattr(result, "markdown_full", None) or getattr(result, "text_full", None):
                return {
                    "job_id": job_id,
                    "markdown_full": getattr(result, "markdown_full", None),
                    "text_full": getattr(result, "text_full", None),
                    "items": self._to_plain_data(getattr(result, "items", None)),
                }

            if status in {"FAILED", "ERROR", "CANCELLED"}:
                raise RuntimeError(f"LlamaParse job failed. job_id={job_id}, status={status}")

            await asyncio.sleep(3)

    def _to_plain_data(self, value):
        if value is None:
            return None

        if hasattr(value, "model_dump"):
            return value.model_dump()

        if isinstance(value, dict):
            return value

        if isinstance(value, list):
            return [self._to_plain_data(v) for v in value]

        if hasattr(value, "__dict__"):
            return {
                key: self._to_plain_data(val)
                for key, val in value.__dict__.items()
                if not key.startswith("_")
            }

        return value