from pydantic import BaseModel
from typing import Optional, Literal

class Change(BaseModel):
    type: Literal["added", "removed", "modified"]
    entity: str
    layer: Optional[str] = None
    location: Optional[dict] = None
    before: Optional[dict] = None
    after: Optional[dict] = None
    region_crop: Optional[str] = None

class DiffResult(BaseModel):
    revision_a: str
    revision_b: str
    confidence: Literal["exact", "visual-estimate"]
    changes: list[Change]