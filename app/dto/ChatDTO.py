from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatQueryRequest(BaseModel):
    query: str
    session_id: str 
    action_context: Optional[Dict[str, Any]] = None

class ChatQueryResponse(BaseModel):
    answer: str
    context: List[str] 
    action_type: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None 