from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field


class BulkItemType(str, enum.Enum):
    notes = "notes"
    links = "links"


class BulkAction(str, enum.Enum):
    add = "add"
    remove = "remove"


class BulkTagsRequest(BaseModel):
    """Apply or remove one or more tags across multiple notes or links."""

    item_type: BulkItemType
    item_ids: list[uuid.UUID] = Field(min_length=1)
    action: BulkAction
    tag_ids: list[uuid.UUID] = Field(min_length=1)


class BulkTagsResponse(BaseModel):
    updated_items: list[uuid.UUID]
    applied_tags: list[uuid.UUID]
    action: BulkAction
