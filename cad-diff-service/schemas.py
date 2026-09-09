from pydantic import BaseModel
from typing import Optional, Literal

class Change(BaseModel):
    type: Literal["added", "removed", "modified"]
    entity: str
    layer: Optional[str] = None
    location: Optional[dict] = None
    location_label: Optional[str] = None
    description: Optional[str] = None
    before: Optional[dict] = None
    after: Optional[dict] = None
    region_crop: Optional[str] = None
    redline_bbox: Optional[list] = None

class DiffResult(BaseModel):
    revision_a: str
    revision_b: str
    confidence: Literal["exact", "visual-estimate"]
    changes: list[Change]
    redline_pdf: Optional[str] = None