import uuid

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

# from .demo_resource import DemoResource

if TYPE_CHECKING:
    from .demo_resource import DemoResource


class CategoryCreate(SQLModel):
    name: str = Field(max_length=12)
    description: Optional[str] = None


class Category(CategoryCreate, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)

    demo_resources: List["DemoResource"] = Relationship(
        back_populates="category", sa_relationship_kwargs={"lazy": "selectin"}
    )


class CategoryUpdate(CategoryCreate):
    name: Optional[str] = None


class CategoryRead(CategoryCreate):
    id: uuid.UUID


# class CategoryReadWithDemoResources(Category):
#     demo_resources: List[DemoResource] = []
