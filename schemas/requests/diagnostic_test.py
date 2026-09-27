from pydantic import BaseModel
from typing import Optional


class CreateDiagnosticTestRequest(BaseModel):
    name: str
    description: str
    image_url: Optional[str] = None
