from pydantic import BaseModel
from typing import Dict, Any


class WebhookData(BaseModel):
    provider: str
    raw_payload: Dict[str, Any]
    headers: Dict[str, str]
