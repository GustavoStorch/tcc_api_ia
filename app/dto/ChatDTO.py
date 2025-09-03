from pydantic import BaseModel
from typing import List

class ChatQueryRequest(BaseModel):
    query: str
    session_id: str 

class ChatQueryResponse(BaseModel):
    answer: str
    context: List[str] 