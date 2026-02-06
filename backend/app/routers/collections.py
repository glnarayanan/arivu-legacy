"""
Collections router - extracted from server.py (Phase 4, Plan 01).

Manages user bookmark collections: create, list, and add bookmarks.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, validator

from app.core.database import get_database
from app.core.dependencies import get_current_user

router = APIRouter(tags=["collections"])


# --- Pydantic Models ---


class Collection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    bookmark_ids: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollectionCreate(BaseModel):
    name: str

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Collection name cannot be empty")
        if len(v) > 100:
            raise ValueError("Collection name too long (max 100 characters)")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Collection name contains invalid characters")
        return v.strip()


class AddToCollection(BaseModel):
    bookmark_id: str


# --- Endpoints ---


@router.post("/collections", response_model=Collection)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    collection = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": collection_data.name,
        "bookmark_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.collections.insert_one(collection)
    return Collection(**collection)


@router.get("/collections", response_model=List[Collection])
async def get_collections(current_user: dict = Depends(get_current_user)):
    db = get_database()
    collections = (
        await db.collections.find({"user_id": current_user["id"]}, {"_id": 0})
        .limit(100)
        .to_list(None)
    )
    return [Collection(**c) for c in collections]


@router.post("/collections/{collection_id}/add")
async def add_to_collection(
    collection_id: str,
    data: AddToCollection,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    result = await db.collections.update_one(
        {"id": collection_id, "user_id": current_user["id"]},
        {"$addToSet": {"bookmark_ids": data.bookmark_id}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Bookmark added to collection"}
