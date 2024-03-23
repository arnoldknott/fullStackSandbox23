import uuid
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Generic, Type, TypeVar, Optional

from models.access import AccessPolicy
from crud.access import AccessPolicyCRUD
from core.databases import get_async_session
from core.access import AccessControl
from fastapi import HTTPException
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


if TYPE_CHECKING:
    pass
from core.types import CurrentUserData, Action, ResourceType, IdentityType

logger = logging.getLogger(__name__)

# access_control = core.access_control.AccessControl()
# access_control = AccessControl()
read = Action.read
write = Action.write
own = Action.own

BaseModelType = TypeVar("BaseModelType", bound=SQLModel)
BaseSchemaTypeCreate = TypeVar("BaseSchemaTypeCreate", bound=SQLModel)
BaseSchemaTypeRead = TypeVar("BaseSchemaTypeRead", bound=SQLModel)
BaseSchemaTypeUpdate = TypeVar("BaseSchemaTypeUpdate", bound=SQLModel)


class BaseCRUD(
    Generic[
        BaseModelType,
        BaseSchemaTypeCreate,
        BaseSchemaTypeRead,
        BaseSchemaTypeUpdate,
    ]
):
    """Base class for CRUD operations."""

    def __init__(
        self,
        base_model: Type[BaseModelType],
        # resource_type: "ResourceType" = None,
        # TBD: consider moving this to the access_control as an override and method specific parameter
        # The endpoints can still be protected by token claims individually - just add UserRoles or a scope requirement to the endpoint
    ):
        """Provides a database session for CRUD operations."""
        self.session = None
        self.model = base_model
        # print("=== BaseCRUD - ResourceType._member_names ===")
        # print(ResourceType._member_names_)
        # print("=== BaseCRUD - ResourceType.__members__.values ===")
        # print(ResourceType.__members__.values())
        # print("=== BaseCRUD - ResourceType._member_map_.values() ===")
        # print(ResourceType._member_map_.values())
        # print("=== BaseCRUD - IdentityType.__members__ ===")
        # print(IdentityType.__members__)
        # print("=== BaseCRUD -  ResourceType.list() ===")
        # print(ResourceType.list())
        # print("=== BaseCRUD - base_model.__name__ ===")
        # print(base_model.__name__)
        if base_model.__name__ in ResourceType.list():
            # print("=== BaseCRUD - ResourceType(base_model.__name__) ===")
            # print(ResourceType(base_model.__name__))
            self.resource_type = ResourceType(base_model.__name__)
        elif base_model.__name__ in IdentityType.list():
            self.resource_type = IdentityType(base_model.__name__)
        else:
            raise ValueError(
                f"{base_model.__name__} is not a valid ResourceType or IdentityType"
            )
        # self.resource_type = ResourceType(base_model.__name__)
        self.policy_CRUD = AccessPolicyCRUD()
        self.access_control = AccessControl(self.policy_CRUD)

    async def __aenter__(self) -> AsyncSession:
        """Returns a database session."""
        self.session = await get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the database session."""
        await self.session.close()

    async def create(
        self,
        object: BaseSchemaTypeCreate,
        # update_last_access: bool = True,  # Refactor: remove this parameter and make it part of the access control checks, as well as the access_logs_table
        # Refactor into this:
        current_user: Optional["CurrentUserData"] = None,
    ) -> BaseModelType:
        """Creates a new object."""
        logger.info("BaseCRUD.create")
        # TBD: add access control checks here:
        # request is known from self.current_user, object and method is write here
        try:
            # TBD: remove the self.public completely - all handled by fine grained access control now.
            # For public, there's a public override in the access control checks.
            # print("=== BaseCRUD.create - current_user ===")
            # print(current_user)
            # print("=== BaseCRUD.create - type(current_user) ===")
            # print(type(current_user))
            # Not necessary here - anybody how passed the endpoint guards can create anything!
            # But use this protection for all read, update and delete methods!
            # Remove the public and refactor, e.g. for the demo resource to create as public -
            # see second session.add() comment below
            # if not await self.access_control.allows(
            #     user=current_user,
            #     resource_type=self.resource_type,
            #     action=write,
            # ):
            #     raise HTTPException(status_code=403, detail="Access denied")
            session = self.session
            Model = self.model
            database_object = Model.model_validate(object)
            # TBD: refactor into access control
            # if hasattr(database_object, "last_accessed_at") and update_last_access is True:
            #     database_object.last_accessed_at = datetime.now()
            session.add(database_object)
            await session.commit()
            await session.refresh(database_object)
            access_policy = None
            # TBD move the choice about public resources to access_CRUD!
            if current_user is not None:
                access_policy = AccessPolicy(
                    resource_id=database_object.id,
                    resource_type=self.resource_type,
                    action=own,
                    identity_id=current_user.user_id,
                    identity_type=IdentityType.user,
                )
            else:
                access_policy = AccessPolicy(
                    resource_id=database_object.id,
                    resource_type=self.resource_type,
                    action=own,
                    public=True,
                )
            # print("=== BaseCRUD.create - access_policy ===")
            # print(access_policy)
            # async with self.policy_CRUD as policy_CRUD:
            #     await policy_CRUD.create(access_policy)
            # TBD: put access policy creation here!
            # Ideally in the same database transaction as above with another session.add() and same session.commit()
            # TBD: add access log here!
            return database_object
        except Exception as e:
            # TBD: add access logging here!
            logger.error(f"Error in BaseCRUD.create: {e}")
            raise HTTPException(status_code=404, detail="Object not found")

    # TBD: implement a create_if_not_exists method

    # TBD: add skip and limit
    # async def read_all(self, skip: int = 0, limit: int = 100)  -> list[BaseModelType]:
    # Changing to return BaseSchemaTypeRead instead of BaseModelType makes read_with_childs obsolete!
    async def read_all(
        self, current_user: Optional["CurrentUserData"] = None
    ) -> list[BaseSchemaTypeRead]:
        # TBD: add access control checks here:
        # request is known from self.current_user, object and method is read here
        """Returns all objects."""
        session = self.session
        model = self.model
        # TBD: refactor into try-except block and add logging
        # Fetch all access policies for the current user

        # TBD: version before refactoring:
        # statement = select(model)
        # TBD: Refactor into access control:
        # Nope:
        # accessible_object_ids = await self.access_control.finds_allowed(
        #     resource_type=self.resource_type,
        #     action=read,
        #     user=current_user,
        # )
        # statement = select(model).where(model.id.in_(accessible_object_ids))
        # Yes - this looks like the right way to do it:
        join_conditions = self.access_control.filters_allowed(
            resource_type=self.resource_type,
            action=read,
            user=current_user,
        )
        statement = (
            select(model)
            .join(AccessPolicy, model.id == AccessPolicy.resource_id)
            .where(*join_conditions)
        )
        # print("=== BaseCRUD.read_all - statement ===")
        # print(statement)
        # statement = select(self.model).offset(skip).limit(limit)
        response = await session.exec(statement)
        if response is None:
            # TBD: add access logging here!
            raise HTTPException(status_code=404, detail="No objects found")
        # TBD: add access logging here!
        return response.all()

    # Changing to return BaseSchemaTypeRead instead of BaseModelType makes read_with_childs obsolete!
    async def read_by_id(
        self,
        object_id: uuid.UUID,
        current_user: Optional["CurrentUserData"] = None,
        # update_last_access: bool = True,  # Refactor: remove this parameter and make it part of the access control checks, as well as the access_logs_table
        # Refactor into this:
        # current_user: Optional["CurrentUserData"] = None,
    ) -> BaseSchemaTypeRead:
        # TBD: add access control checks here:
        # request is known from self.current_user, object and method is read here
        """Returns an object by id."""
        # if not await self.access_control.allows(
        #     user=current_user,
        #     resource_id=object_id,
        #     resource_type=self.resource_type,
        #     action=read,
        # ):
        #     raise HTTPException(status_code=403, detail="Access denied")
        session = self.session
        model = self.model
        join_conditions = self.access_control.filters_allowed(
            resource_type=self.resource_type,
            action=read,
            user=current_user,
        )
        # generically get the primary key of a model:
        # primary_key = next(iter(model.__table__.primary_key.columns)).name
        # object = await session.get(model, object_id)
        # if object is None:
        #     # TBD: add access logging here!
        #     raise HTTPException(status_code=404, detail="Object not found")
        try:
            # print("=== BaseCRUD.read_by_id - model.id ===")
            # print(model.id)
            # print("=== BaseCRUD.read_by_id - object_id ===")
            # print(object_id)
            statement = (
                select(model).where(model.id == object_id)
                # .join(AccessPolicy, model.id == AccessPolicy.resource_id)
                # .where(*join_conditions)
            )
            response = await session.exec(statement)
            object = response.one()
            # statement = select(model).where(model.id == object_id)
            # response = await session.exec(statement)
            # object = response.one()
        except Exception as e:
            # TBD: add access logging here!
            logger.error(f"Error in BaseCRUD.read_by_id: {e}")
            raise HTTPException(status_code=404, detail="Object not found")
        # TBD: Refactor into access control
        # if hasattr(object, "last_accessed_at") and update_last_access is True:
        #     model.last_accessed_at = datetime.now()
        #     session.add(object)
        #     await session.commit()
        #     await session.refresh(object)
        # TBD: add access logging here!
        return object

    async def update(
        self,
        old: BaseModelType,
        new: BaseSchemaTypeUpdate,
        # update_last_access: bool = True,  # Refactor: remove this parameter and make it part of the access control checks, as well as the access_logs_table
        # Refactor into this:
        # current_user: "CurrentUserData",
    ) -> BaseModelType:
        # TBD: add access control checks here:
        # request is known from self.current_user, object and method is write here
        """Updates an object."""
        session = self.session
        # TBD: refactor into try-except block and add logging
        if hasattr(old, "last_updated_at"):
            old.last_updated_at = datetime.now()
        # TBD: Refactor into access control
        # if hasattr(old, "last_accessed_at") and update_last_access is True:
        #     old.last_accessed_at = datetime.now()
        updated = new.model_dump(exclude_unset=True)
        for key, value in updated.items():
            # if key == "id" or key == "created_at" or key == "last_updated_at":
            if (
                key == "created_at"
                or key == "last_updated_at"
                # or key == "last_accessed_at"
            ):
                continue
            setattr(old, key, value)
        object = old
        session.add(object)
        await session.commit()
        await session.refresh(object)
        # TBD: add exception handling here!
        # TBD: add access logging here!
        return object

    async def delete(self, object_id: uuid.UUID) -> BaseModelType:
        # TBD: add access control checks here:
        # request is known from self.current_user, object and method is write or delete here
        """Deletes an object."""
        session = self.session
        model = self.model
        # TBD: refactor into try-except block and add logging
        object = await session.get(model, object_id)
        if object is None:
            raise HTTPException(status_code=404, detail="Object not found")
        await session.delete(object)
        await session.commit()
        return object  #

    # TBD: add share / permission methods - maybe in an inherited class BaseCRUDPermissions?
