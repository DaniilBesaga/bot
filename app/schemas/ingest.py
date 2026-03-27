from pydantic import BaseModel


class IngestResponse(BaseModel):
    message: str
    results: list[dict]