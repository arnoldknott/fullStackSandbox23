import logging
from uuid import UUID

# from typing import List
from fastapi import APIRouter, Depends, HTTPException

from core.security import get_access_token_payload, Guards
from core.types import GuardTypes
from .base import BaseView

from crud.category import CategoryCRUD

from models.category import Category, CategoryCreate, CategoryUpdate, CategoryRead
from models.demo_resource import DemoResource

logger = logging.getLogger(__name__)
router = APIRouter()

category_view = BaseView(CategoryCRUD, Category)

# # TBD delete version before refactoring:
# @router.post("/", status_code=201)
# async def post_category(
#     category: CategoryCreate,
# ) -> Category:
#     """Creates a new category."""
#     logger.info("POST category")
#     async with CategoryCRUD() as crud:
#         created_category = await crud.create(category)
#     return created_category


@router.post("/", status_code=201)
async def post_category(
    category: CategoryCreate,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Category:
    """Creates a new category."""
    return await category_view.post(
        category,
        token_payload,
        guards,
        # scopes=["api.write"],
        # roles=["User"],
    )


# # TBD delete version before refactoring:
# @router.get("/", status_code=200)
# async def get_all_categories() -> List[Category]:
#     """Returns all categories."""
#     logger.info("GET all categories")
#     async with CategoryCRUD() as crud:
#         response = await crud.read_all()
#     return response

# @router.get("/{category_id}")
# async def get_category_by_id(category_id: UUID) -> Category:
#     """Returns a category."""
#     logger.info("GET category")
#     try:
#         category_id = uuid.UUID(category_id)
#     except ValueError:
#         logger.error("Category ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid category id")
#     async with CategoryCRUD() as crud:
#         response = await crud.read_by_id(category_id)
#     return response


@router.get("/", status_code=200)
async def get_categories(
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(roles=["User"])),
) -> list[CategoryRead]:
    """Returns all category."""
    return await category_view.get(
        token_payload,
        guards,
        # roles=["User"],
    )


@router.get("/{category_id}", status_code=200)
async def get_category_by_id(
    category_id: UUID,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(roles=["User"])),
) -> CategoryRead:
    """Returns a category."""
    return await category_view.get_by_id(
        category_id,
        token_payload,
        guards,
        # roles=["User"],
    )


# # TBD delete version before refactoring:
# @router.put("/{category_id}")
# async def update_category(
#     category_id: UUID,
#     category: CategoryUpdate,
# ) -> Category:
#     """Updates a category."""
#     logger.info("PUT category")
#     try:
#         category_id = uuid.UUID(category_id)
#     except ValueError:
#         logger.error("Category ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid category id")
#     async with CategoryCRUD() as crud:
#         old_category = await crud.read_by_id(category_id)
#         response = await crud.update(old_category, category)
#     return response


@router.put("/{category_id}", status_code=200)
async def put_category(
    category_id: UUID,
    category: CategoryUpdate,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Category:
    """Updates a category."""
    return await category_view.put(
        category_id,
        category,
        token_payload,
        guards,
        # roles=["User"],
        # scopes=["api.write"],
    )


# @router.delete("/{category_id}")
# async def delete_category(category_id: UUID) -> Category:
#     """Deletes a category."""
#     logger.info("DELETE category")
#     try:
#         category_id = UUID(category_id)
#     except ValueError:
#         logger.error("Category ID is not a universal unique identifier (uuid).")
#         raise HTTPException(status_code=400, detail="Invalid category id")
#     async with CategoryCRUD() as crud:
#         response = await crud.delete(category_id)
#     return response


@router.delete("/{category_id}", status_code=200)
async def delete_category(
    category_id: UUID,
    token_payload=Depends(get_access_token_payload),
    guards: GuardTypes = Depends(Guards(scopes=["api.write"], roles=["User"])),
) -> Category:
    """Deletes a category."""
    return await category_view.delete(
        category_id, token_payload, guards  # roles=["User"], scopes=["api.write"]
    )


# TBD: refactor to updated access protection
@router.get("/{category_id}/demoresources")
async def get_all_demo_resources_in_category(category_id: UUID) -> list[DemoResource]:
    """Returns all demo resources within category."""
    logger.info("GET all demo resources within category")
    # try:
    #     category_id = UUID(category_id)
    # except ValueError:
    #     logger.error("Category ID is not a universal unique identifier (uuid).")
    #     raise HTTPException(status_code=400, detail="Invalid category id")
    async with CategoryCRUD() as crud:
        response = await crud.read_all_demo_resources(category_id)
    return response
