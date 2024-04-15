import logging
import uuid

from crud.tag import TagCRUD
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_access_token_payload, Guards
from core.types import GuardTypes
from .base import BaseView
from models.demo_resource import DemoResource
from models.tag import Tag, TagCreate, TagRead, TagUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

tag_view = BaseView(TagCRUD, Tag)

# # TBD delete version before refactoring:
# @router.post("/", status_code=201)
# async def post_tag(
#     tag: TagCreate,
# ) -> Tag:
#     """Creates a new tag."""
#     logger.info("POST tag")
#     async with TagCRUD() as crud:
#         created_tag = await crud.create(tag)
#     return created_tag


@router.post("/", status_code=201)
async def post_tag(
    category: TagCreate,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Tag:
    """Creates a new tag."""
    return await tag_view.post_with_public_access(
        category,
        token_payload,
        guards,
        # scopes=["api.write"],
        # roles=["User"],
    )


# # TBD delete version before refactoring:
# @router.get("/", status_code=200)
# async def get_all_tags() -> list[Tag]:
#     """Returns all tags."""
#     logger.info("GET all tags")
#     async with TagCRUD() as crud:
#         response = await crud.read_all()
#     return response

# @router.get("/{tag_id}")
# async def get_tag_by_id(tag_id: str) -> Tag:
#     """Returns a tag."""
#     logger.info("GET tag")
#     try:
#         tag_id = uuid.UUID(tag_id)
#     except ValueError:
#         logger.error("Tag ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid tag id")
#     async with TagCRUD() as crud:
#         response = await crud.read_by_id(tag_id)
#     return response


@router.get("/", status_code=200)
async def get_tags() -> list[TagRead]:
    """Returns all tags."""
    return await tag_view.get()


@router.get("/{tag_id}", status_code=200)
async def get_tag_by_id(
    tag_id: str,
) -> TagRead:
    """Returns a tag."""
    return await tag_view.get_by_id(tag_id)


# # TBD delete version before refactoring:
# @router.put("/{tag_id}")
# async def update_tag(
#     tag_id: str,
#     tag: TagUpdate,
# ) -> Tag:
#     """Updates a tag."""
#     logger.info("PUT tag")
#     try:
#         tag_id = uuid.UUID(tag_id)
#     except ValueError:
#         logger.error("Tag ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid tag id")
#     async with TagCRUD() as crud:
#         old_tag = await crud.read_by_id(tag_id)
#         response = await crud.update(old_tag, tag)
#     return response


@router.put("/{tag_id}", status_code=200)
async def put_tag(
    tag_id: str,
    tag: TagUpdate,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Tag:
    """Updates a tag."""
    return await tag_view.put(
        tag_id,
        tag,
        token_payload,
        guards,
        # roles=["User"],
        # scopes=["api.write"],
    )


# # TBD delete version before refactoring:
# @router.delete("/{tag_id}")
# async def delete_tag(tag_id: str) -> Tag:
#     """Deletes a tag."""
#     logger.info("DELETE tag")
#     try:
#         tag_id = uuid.UUID(tag_id)
#     except ValueError:
#         logger.error("Tag ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid tag id")
#     async with TagCRUD() as crud:
#         response = await crud.delete(tag_id)
#     return response


@router.delete("/{tag_id}", status_code=200)
async def delete_tag(
    tag_id: str,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Tag:
    """Deletes a tag."""
    return await tag_view.delete(
        tag_id, token_payload, guards  # roles=["User"], scopes=["api.write"]
    )


# TBD: missing tests for this endpoint?
# TBD: refactor to updated access protection
@router.get("/{tag_id}/demoresources")
async def get_all_demo_resources_for_tag(tag_id: str) -> list[DemoResource]:
    """Returns all demo resources with tag."""
    logger.info("GET all demo resources with tag")
    try:
        tag_id = uuid.UUID(tag_id)
    except ValueError:
        logger.error("Tag ID is not a universal unique identifier (uuid).")
        raise HTTPException(status_code=400, detail="Invalid tag id")
    async with TagCRUD() as crud:
        response = await crud.read_all_demo_resources(tag_id)
    return response
