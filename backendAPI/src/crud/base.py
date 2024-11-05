import logging
import uuid
from os import makedirs, path, rename
from typing import TYPE_CHECKING, Generic, List, Optional, Type, TypeVar

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased, class_mapper, contains_eager, foreign, noload
from sqlmodel import SQLModel, asc, delete, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.databases import get_async_session
from crud.access import (
    AccessLoggingCRUD,
    AccessPolicyCRUD,
    BaseHierarchyModelRead,
    IdentityHierarchyCRUD,
    ResourceHierarchyCRUD,
)
from models.access import (
    AccessLogCreate,
    AccessPolicyCreate,
    AccessPolicyDelete,
    IdentifierTypeLink,
    IdentityHierarchy,
    ResourceHierarchy,
)

if TYPE_CHECKING:
    pass
from core.types import Action, CurrentUserData, IdentityType, ResourceType

logger = logging.getLogger(__name__)

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
    ],
):
    """Base class for CRUD operations."""

    def __init__(self, base_model: Type[BaseModelType], directory: str = None):
        """Provides a database session for CRUD operations."""
        self.session = None
        self.model = base_model
        self.data_directory = directory
        if base_model.__name__ in ResourceType.list():
            self.entity_type = ResourceType(self.model.__name__)
            self.type = ResourceType
            self.hierarchy_CRUD = ResourceHierarchyCRUD()
            self.hierarchy = ResourceHierarchy
            self.relations = ResourceHierarchy.relations
        elif base_model.__name__ in IdentityType.list():
            # print("=== CRUD - base - IdentityType ===")
            # print(IdentityType(self.model))
            # print("=== CRUD - base - IdentityType.model.__name__ ===")
            # print(IdentityType(self.model.__name__))
            self.entity_type = IdentityType(self.model.__name__)
            self.type = IdentityType
            self.hierarchy_CRUD = IdentityHierarchyCRUD()
            self.hierarchy = IdentityHierarchy
            self.relations = IdentityHierarchy.relations
        else:
            raise ValueError(
                f"{base_model.__name__} is not a valid ResourceType or IdentityType"
            )

        # TBD: move to to the init: get all possible parent-child relations for the entity_type there!

        # if self.entity_type in ResourceType:
        #     related_model = ResourceType.get_model(relationship.mapper.class_.__name__)

        # elif self.entity_type in IdentityType:
        #     related_model = IdentityType.get_model(relationship.mapper.class_.__name__)

        self.policy_CRUD = AccessPolicyCRUD()
        self.logging_CRUD = AccessLoggingCRUD()
        # moved to the if-block to check which hierarchy is relevant.
        # self.hierarchy_CRUD = (
        #     ResourceHierarchyCRUD()
        # )  # TBD. are the occasions, where I would need the IdentityHierarchyCRUD() here?

    async def __aenter__(self) -> AsyncSession:
        """Returns a database session."""
        self.session = await get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the database session."""
        await self.session.close()

    # async def _write_policy(
    #     self,
    #     resource_id: uuid.UUID,
    #     action: Action,
    #     current_user: "CurrentUserData",
    # ):
    #     """Creates an access policy entry."""
    #     access_policy = AccessPolicy(
    #         resource_id=resource_id,
    #         action=action,
    #         identity_id=current_user.user_id,
    #     )
    #     # This needs a round-trip to database, as the policy-CRUD takes care of access control
    #     async with self.policy_CRUD as policy_CRUD:
    #         await policy_CRUD.create(access_policy, current_user)

    # move to AccessLoggingCRUD or use/rewrite the on log_access from there?
    # def _add_log_to_session(
    #     self,
    #     object_id: uuid.UUID,
    #     action: Action,
    #     current_user: "CurrentUserData",
    #     status_code: int,
    # ):
    #     """Creates an access log entry."""
    #     access_log = AccessLog(
    #         resource_id=object_id,
    #         action=action,
    #         identity_id=current_user.user_id if current_user else None,
    #         status_code=status_code,
    #     )
    #     self.session.add(access_log)

    # async def _write_log(
    #     self,
    #     object_id: uuid.UUID,
    #     action: Action,
    #     current_user: "CurrentUserData",
    #     status_code: int,
    # ):
    #     """Creates an access log entry."""
    #     self._add_log_to_session(object_id, action, current_user, status_code)
    #     await self.session.commit()

    def _add_identifier_type_link_to_session(
        self,
        object_id: uuid.UUID,
    ):
        """Adds resource type link entry to session."""
        identifier_type_link = IdentifierTypeLink(
            id=object_id,
            type=self.entity_type,
        )

        statement = insert(IdentifierTypeLink).values(identifier_type_link.model_dump())
        statement = statement.on_conflict_do_nothing(index_elements=["id"])
        return statement

    async def _write_identifier_type_link(
        self,
        object_id: uuid.UUID,
    ):
        """Creates an resource type link entry."""
        statement = self._add_identifier_type_link_to_session(object_id)
        await self.session.exec(statement)
        await self.session.commit()

    # async def _delete_identifier_type_link(
    #     self,
    #     object_id: uuid.UUID,
    # ):
    #     """Deletes a resource type link entry."""
    #     statement = delete(IdentifierTypeLink).where(IdentifierTypeLink.id == object_id)
    #     await self.session.exec(statement)
    #     await self.session.commit()

    async def _check_identifier_type_link(
        self,
        object_id: uuid.UUID,
    ):
        """Checks if a resource type link of an object_id refers to a type self_model."""
        statement = select(IdentifierTypeLink).where(
            IdentifierTypeLink.id == object_id,
            IdentifierTypeLink.type == self.entity_type,
        )
        response = await self.session.exec(statement)
        result = response.unique().one()
        if not result:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found."
            )
        return True

    def _provide_data_directory(
        self,
    ):
        """Checks if a file path exists and if not creates it."""
        try:
            if not path.exists(f"/data/appdata/{self.data_directory}"):
                makedirs(f"/data/appdata/{self.data_directory}")
            return True
        except Exception as e:
            raise Exception(f"Path not found: {e}")

    async def create(
        self,
        object: BaseSchemaTypeCreate,
        current_user: "CurrentUserData",
        parent_id: Optional[uuid.UUID] = None,
        inherit: Optional[bool] = False,
    ) -> BaseModelType:
        """Creates a new object."""
        logger.info("BaseCRUD.create")
        try:
            # TBD: refactor into hierarchy check
            # requires hierarchy checks to be in place: otherwise a user can never create a resource
            # as the AccessPolicy CRUD create checks, if the user is owner of the resource (that's not created yet)
            # needs to be fixed in the core access control by implementing a hierarchy check
            if inherit and not parent_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot inherit permissions without a parent.",
                )
            database_object = self.model.model_validate(object)
            # print("=== CRUD - base - create - database_object ===")
            # pprint(database_object)
            await self._write_identifier_type_link(database_object.id)
            self.session.add(database_object)
            # await self.session.commit()
            # await self.session.refresh(database_object)
            access_log = AccessLogCreate(
                resource_id=database_object.id,
                action=own,
                identity_id=current_user.user_id,
                status_code=201,
            )
            async with self.logging_CRUD as logging_CRUD:
                await logging_CRUD.create(access_log)
            # self.session = self.logging_CRUD.add_log_to_session(
            #     access_log, self.session
            # )
            # await self._add_log_to_session(database_object.id, own, current_user, 201)

            # TBD: merge the sessions for creating the policy and the log
            # maybe together with creating the object
            # but we need the id of the object for the policy and the log
            # The id is already available after model_validate!
            # TBD: add creating the ResourceTypeLink entry with object_id and self.entity_type
            # this should be doable in the same database call as the access policy and the access log creation.
            # self._add_identifier_type_link_to_session(database_object.id)
            await self.session.commit()
            await self.session.refresh(database_object)
            # TBD: create the statements in the methods, but execute together - less round-trips to database
            # await self._write_identifier_type_link(database_object.id)
            # await self._write_policy(database_object.id, own, current_user)
            access_policy = AccessPolicyCreate(
                resource_id=database_object.id,
                action=own,
                identity_id=current_user.user_id,
            )
            async with self.policy_CRUD as policy_CRUD:
                await policy_CRUD.create(access_policy, current_user)
            # await self._write_log(database_object.id, own, current_user, 201)
            if parent_id:
                await self.add_child_to_parent(
                    parent_id=parent_id,
                    child_id=database_object.id,
                    current_user=current_user,
                    inherit=inherit,
                )
                # async with self.hierarchy_CRUD as hierarchy_CRUD:
                #     await hierarchy_CRUD.create(
                #         current_user=current_user,
                #         parent_id=parent_id,
                #         child_type=self.entity_type,
                #         child_id=database_object.id,
                #         inherit=inherit,
                #     )

            # print("=== CRUD - base - create - database_object ===")
            # pprint(database_object)

            return database_object

        except Exception as e:
            try:
                access_log = AccessLogCreate(
                    resource_id=database_object.id,
                    action=own,
                    identity_id=current_user.user_id,
                    status_code=404,
                )
                async with self.logging_CRUD as logging_CRUD:
                    await logging_CRUD.create(access_log)
                # await self._write_log(database_object.id, own, current_user, 404)
            except Exception as log_error:
                logger.error(
                    f"Error in BaseCRUD.create of an object of type {self.model}, action: {own}, current_user: {current_user}, status_code: {404} results in  {log_error}"
                )
            logger.error(f"Error in BaseCRUD.create: {e}")
            raise HTTPException(
                status_code=403,
                detail=f"{self.model.__name__} - Forbidden.",
            )

    async def create_file(
        self,
        file: UploadFile,
        current_user: "CurrentUserData",
        parent_id: Optional[uuid.UUID] = None,
        inherit: Optional[bool] = False,
    ) -> BaseModelType:
        """Creates new files."""
        file_object = await self.create(
            object={"name": file.filename},
            current_user=current_user,
            parent_id=parent_id,
            inherit=inherit,
        )
        try:
            self._provide_data_directory()
            disk_file = open(
                f"/data/appdata/{self.data_directory}/{file.filename}", "wb"
            )
            disk_file.write(file.file.read())
            return file_object
        except Exception as e:
            logger.error(f"Error in BaseCRUD.create_file {file.filename}: {e}")
            raise HTTPException(
                status_code=403,
                detail=f"{self.model.__name__} - Forbidden.",
            )

    async def create_public(
        self,
        object: BaseSchemaTypeCreate,
        current_user: "CurrentUserData",
        parent_id: Optional[uuid.UUID] = None,
        inherit: Optional[bool] = False,
        action: Action = read,
    ) -> BaseModelType:
        """Creates a new object with public access."""
        database_object = await self.create(object, current_user, parent_id, inherit)

        public_access_policy = AccessPolicyCreate(
            resource_id=database_object.id,
            action=action,
            public=True,
        )
        async with self.policy_CRUD as policy_CRUD:
            await policy_CRUD.create(public_access_policy, current_user)

        return database_object

    async def add_child_to_parent(
        self,
        child_id: uuid.UUID,
        parent_id: uuid.UUID,
        current_user: "CurrentUserData",
        inherit: Optional[bool] = False,
    ) -> BaseHierarchyModelRead:
        """Adds a member of this class to a parent (of another entity type)."""
        async with self.hierarchy_CRUD as hierarchy_CRUD:
            hierarchy = await hierarchy_CRUD.create(
                current_user=current_user,
                parent_id=parent_id,
                child_type=self.entity_type,
                child_id=child_id,
                inherit=inherit,
            )

        return hierarchy

    # TBD: implement a create_if_not_exists method

    # TBD: add skip and limit
    # use with pagination:
    # Model = await model_crud.read(order_by=[Model.name], limit=10)
    # Model = await model_crud.read(order_by=[Model.name], limit=10, offset=10)
    async def read(  # noqa: C901
        self,
        current_user: Optional["CurrentUserData"] = None,
        select_args: Optional[List] = None,
        filters: Optional[List] = None,
        joins: Optional[List] = None,
        order_by: Optional[List] = None,
        group_by: Optional[List] = None,
        having: Optional[List] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[BaseSchemaTypeRead]:
        # TBD: consider allowing any return value - that might enable more flexibility, especially for select_args and functions!
        """Generic read method with optional parameters for select_args, filters, joins, order_by, group_by, limit and offset."""
        try:
            # TBD: select_args are not compatible with the return type of the method!
            statement = select(*select_args) if select_args else select(self.model)
            # statement = (
            #     self.session.select(*select_args)
            #     if select_args
            #     else self.session.select(self.model)
            # )

            statement = self.policy_CRUD.filters_allowed(
                statement=statement,
                action=read,
                model=self.model,
                current_user=current_user,
            )

            # query relationships:
            for relationship in class_mapper(self.model).relationships:
                # Determine the related model, the relevant hierarchy and relations based on self.entity_type
                related_model = self.type.get_model(relationship.mapper.class_.__name__)
                related_attribute = getattr(self.model, relationship.key)
                related_type = self.type(related_model.__name__)
                related_statement = select(related_model.id)
                related_statement = self.policy_CRUD.filters_allowed(
                    related_statement,
                    action=read,
                    model=related_model,
                    current_user=current_user,
                )

                # Check if self.entity_type is a key in relations, i.e. the model is a parent in the hierarchy
                aliased_hierarchy = aliased(self.hierarchy)
                for parent, children in self.relations.items():
                    if self.entity_type == parent and related_type in children:
                        # self.model is a parent, join on parent_id
                        statement = statement.outerjoin(
                            aliased_hierarchy,
                            self.model.id == foreign(aliased_hierarchy.parent_id),
                        )
                        statement = statement.outerjoin(
                            related_model,
                            related_model.id == foreign(aliased_hierarchy.child_id),
                        ).order_by(asc(related_model.id))
                    elif self.entity_type in children and related_type == parent:
                        # self.model is a child, join on child_id
                        statement = statement.outerjoin(
                            aliased_hierarchy,
                            self.model.id == foreign(aliased_hierarchy.child_id),
                        )
                        statement = statement.outerjoin(
                            related_model,
                            related_model.id == foreign(aliased_hierarchy.parent_id),
                        ).order_by(asc(related_model.id))

                count_related_statement = select(func.count()).select_from(
                    related_statement.alias()
                )
                related_count = await self.session.exec(count_related_statement)
                count = related_count.one()

                if count == 0:
                    statement = statement.options(noload(related_attribute))
                else:
                    statement = statement.where(
                        or_(
                            related_model.id
                            == None,  # noqa: E711: comparison to None should be 'if cond is None:'
                            related_model.id.in_(related_statement),
                        )
                    ).options(contains_eager(related_attribute))

            if joins:
                for join in joins:
                    statement = statement.join(join)

            if filters:
                for filter in filters:
                    statement = statement.where(filter)

            if order_by:
                for order in order_by:
                    statement = statement.order_by(order)
            elif hasattr(self.model, "id"):
                statement = statement.order_by(asc(self.model.id))

            if group_by:
                statement = statement.group_by(*group_by)

            if having:
                statement = statement.having(*having)

            if limit:
                statement = statement.limit(limit)

            if offset:
                statement = statement.offset(offset)

            response = await self.session.exec(statement)
            results = response.unique().all()

            if not results:
                logger.info(f"No objects found for {self.model.__name__}")
                raise HTTPException(
                    status_code=404, detail=f"{self.model.__name__} not found."
                )

            for result in results:
                # TBD: add logging to accessed children!
                access_log = AccessLogCreate(
                    resource_id=result.id,  # result might not be available here?
                    action=read,
                    identity_id=current_user.user_id if current_user else None,
                    status_code=200,
                )
                async with self.logging_CRUD as logging_CRUD:
                    await logging_CRUD.create(access_log)

            return results
        except Exception as err:
            try:
                access_log = AccessLogCreate(
                    resource_id=result.id,
                    action=read,
                    identity_id=current_user.user_id if current_user else None,
                    status_code=404,
                )
                async with self.logging_CRUD as logging_CRUD:
                    await logging_CRUD.create(access_log)
            except Exception as log_error:
                logger.error(
                    (
                        f"Error in BaseCRUD.read with parameters:"
                        f"select_args: {select_args},"
                        f"filters: {filters},"
                        f"joins: {joins},"
                        f"order_by: {order_by},"
                        f"group_by: {group_by},"
                        f"having: {having},"
                        f"limit: {limit},"
                        f"offset: {offset},"
                        f"action: {read},"
                        f"current_user: {current_user},"
                        f"status_code: {404}"
                        f"results in {log_error}"
                    )
                )
                logger.error(
                    f"Error in BaseCRUD.read for model {self.model.__name__}: {err}"
                )

                raise HTTPException(
                    status_code=404, detail=f"{self.model.__name__} not found."
                )

    async def read_by_id(
        self,
        id: uuid.UUID,
        current_user: Optional["CurrentUserData"] = None,
    ):
        """Reads an object by id."""

        object = await self.read(
            current_user=current_user,
            filters=[self.model.id == id],
        )
        return object[0]

    async def read_file_by_id(
        self,
        id: uuid.UUID,
        current_user: Optional["CurrentUserData"] = None,
    ):
        """Reads a file from disk by id."""

        file = await self.read_by_id(id, current_user)
        # disk_file = open(f"/data/appdata/{self.data_directory}/{file.name}", "rb")
        # return disk_file
        return FileResponse(
            f"/data/appdata/{self.data_directory}/{file.name}", filename=file.name
        )

    async def update(
        self,
        current_user: "CurrentUserData",
        object_id: uuid.UUID,
        new: BaseSchemaTypeUpdate,
    ) -> BaseModelType:
        """Updates an object."""
        session = self.session

        try:
            statement = select(self.model).where(self.model.id == object_id)

            statement = self.policy_CRUD.filters_allowed(
                statement=statement,
                action=write,
                model=self.model,
                current_user=current_user,
            )
            response = await session.exec(statement)
            old = response.unique().one()
            if old is None:
                logger.info(f"Object with id {object_id} not found")
                raise HTTPException(
                    status_code=404, detail=f"{self.model.__name__} not found."
                )

            updated = new.model_dump(exclude_unset=True)
            for key, value in updated.items():
                setattr(old, key, value)
            object = old
            session.add(object)
            access_log = AccessLogCreate(
                resource_id=object.id,
                action=write,
                identity_id=current_user.user_id,
                status_code=200,
            )
            async with self.logging_CRUD as logging_CRUD:
                await logging_CRUD.create(access_log)
            await session.commit()
            await session.refresh(object)
            return object
        except Exception as e:
            try:
                access_log = AccessLogCreate(
                    resource_id=object.id,
                    action=write,
                    identity_id=current_user.user_id,
                    status_code=404,
                )
                async with self.logging_CRUD as logging_CRUD:
                    await logging_CRUD.create(access_log)
            except Exception as log_error:
                logger.error(
                    f"Error in BaseCRUD.update with parameters object_id: {object_id}, action: {write}, current_user: {current_user}, status_code: {404} results in  {log_error}"
                )
            logger.error(f"Error in BaseCRUD.update: {e}")
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not updated."
            )

    async def update_file(
        self,
        file_id: uuid.UUID,
        current_user: "CurrentUserData",
        file: UploadFile | None,
        metadata: BaseSchemaTypeUpdate | None,
    ) -> BaseModelType:
        """Updates a file."""
        print("=== CRUD - base - update_file ===")
        try:
            if metadata:
                print("=== CRUD - base - update_file - metadata ===")
                old_metadata = await self.read_by_id(file_id, current_user)
                new_metadata = await self.update(current_user, file_id, metadata)
                # TBD: consider adding self._provide_data_directory() here for directory changes
                rename(
                    f"/data/appdata/{self.data_directory}/{old_metadata.name}",
                    f"/data/appdata/{self.data_directory}/{new_metadata.name}",
                )
            # conflict: is ithe the file.name or metadata.name, that decides the filename?
            # TBD: add an update here in any case, even if metadata is None to make sure access checks are executed!
            print("=== CRUD - base - update_file - file ===")
            with open(
                f"/data/appdata/{self.data_directory}/{file.filename}", "wb"
            ) as disk_file:
                print("=== CRUD - base - update_file - write file to disk ===")
                disk_file.write(file.file.read())
            return file
        except Exception as e:
            logger.error(f"Error in BaseCRUD.update_file {file_id}: {e}")
            raise HTTPException(
                status_code=403,
                detail=f"{self.model.__name__} - Forbidden.",
            )

    async def delete(
        self,
        current_user: "CurrentUserData",
        object_id: uuid.UUID,
    ) -> None:  # BaseModelType:
        """Deletes an object."""
        try:
            model_alias = aliased(self.model)
            subquery = (
                select(model_alias.id).distinct().where(model_alias.id == object_id)
            )
            subquery = self.policy_CRUD.filters_allowed(
                statement=subquery,
                action=own,
                model=model_alias,
                current_user=current_user,
            )

            statement = delete(self.model).where(self.model.id.in_(subquery))
            result = await self.session.exec(statement)

            if result.rowcount == 0:
                logger.info(f"Object with id {object_id} not found")
                raise HTTPException(
                    status_code=404, detail=f"{self.model.__name__} not found."
                )
            await self.session.commit()

            access_log = AccessLogCreate(
                resource_id=object_id,
                action=own,
                identity_id=current_user.user_id,
                status_code=200,
            )
            async with self.logging_CRUD as logging_CRUD:
                await logging_CRUD.create(access_log)
            # TBD: delete hierarchy only if exists?
            # TBD: delete hierarchies for both parent_id and child_id

            if self.type == ResourceType:
                delete_policies = AccessPolicyDelete(
                    resource_id=object_id,
                )
            elif self.type == IdentityType:
                delete_policies = AccessPolicyDelete(
                    identity_id=object_id,
                )
            try:
                async with self.policy_CRUD as policy_CRUD:
                    await policy_CRUD.delete(current_user, delete_policies)
            except Exception:
                pass

            # Leave the identifier type link, as it's referred to the log table, which stays even after deletion
            # await self._delete_identifier_type_link(object_id)
            # self.session = self.logging_CRUD.add_log_to_session(
            #     access_log, self.session
            # )
            # self._add_log_to_session(object_id, own, current_user, 200)

            return None

        except Exception as e:
            try:
                access_log = AccessLogCreate(
                    resource_id=object_id,
                    action=own,
                    identity_id=current_user.user_id,
                    status_code=404,
                )
                async with self.logging_CRUD as logging_CRUD:
                    await logging_CRUD.create(access_log)
            except Exception as log_error:
                logger.error(
                    f"Error in BaseCRUD.delete with parameters object_id: {object_id}, action: {own}, current_user: {current_user}, status_code: {404} results in  {log_error}"
                )
            logger.error(f"Error in BaseCRUD.delete: {e}")
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not deleted."
            )

    async def remove_child_from_parent(
        self,
        child_id: uuid.UUID,
        parent_id: uuid.UUID,
        current_user: "CurrentUserData",
    ) -> None:
        """Deletes a member of this class from a parent (of another entity type)."""
        # check if child id refers to a type equal to self.model in identifiertypelink table:
        # if not, raise 404
        # if yes, delete the hierarchy entry
        if await self._check_identifier_type_link(child_id):
            async with self.hierarchy_CRUD as hierarchy_CRUD:
                await hierarchy_CRUD.delete(
                    current_user=current_user,
                    parent_id=parent_id,
                    child_id=child_id,
                )
            return None
        else:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found."
            )

    # TBD: add share / permission methods - maybe in an inherited class BaseCRUDPermissions?
    # TBD: for the hierarchies, do we need more methods here or just a new method in the BaseCRUD?
    # => The AccessPolicyCRUD takes care of this!
    # like sharing, tagging, creating hierarchies etc.
    # or just a number of endpoints for doing the hierarchy: add child, remove child, ...?
    # share with different permissions - like actions?
