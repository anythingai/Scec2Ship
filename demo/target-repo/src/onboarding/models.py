from typing import List, Optional
from pydantic import BaseModel

class ChecklistItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    is_completed: bool = False
    is_required: bool = True

class ChecklistState(BaseModel):
    items: List[ChecklistItem]
    completion_percentage: float
