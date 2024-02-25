# from unittest.mock import AsyncMock, patch

import pytest
from typing import List
from crud.user import UserCRUD
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from models.user import User, UserRead
from fastapi import FastAPI
from tests.utils import (
    token_payload_user_id,
    token_payload_tenant_id,
    token_payload_roles_admin,
    token_payload_roles_user,
    token_payload_scope_api_read,
    token_payload_scope_api_read_write,
    token_payload_one_group,
    one_test_user,
)

## POST tests:


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_user_id,
            **token_payload_tenant_id,
            **token_payload_scope_api_read_write,
            **token_payload_roles_admin,
            **token_payload_one_group,
        }
    ],
    indirect=True,
)
async def test_admin_posts_user(
    async_client: AsyncClient, app_override_get_azure_payload_dependency: FastAPI
):
    """Tests the post_user endpoint of the API."""
    app_override_get_azure_payload_dependency

    # Make a POST request to create the user
    response = await async_client.post(
        "/api/v1/user/",
        json=one_test_user,
    )

    assert response.status_code == 201
    created_user = User(**response.json())
    assert created_user.azure_user_id == one_test_user["azure_user_id"]
    assert created_user.azure_tenant_id == one_test_user["azure_tenant_id"]

    # Verify that the user was created in the database
    async with UserCRUD() as crud:
        db_user = await crud.read_by_azure_user_id(one_test_user["azure_user_id"])
    assert db_user is not None
    db_user_json = jsonable_encoder(db_user)
    assert db_user_json["azure_user_id"] == one_test_user["azure_user_id"]
    assert db_user_json["azure_tenant_id"] == one_test_user["azure_tenant_id"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_user_id,
            **token_payload_tenant_id,
            **token_payload_scope_api_read_write,
            **token_payload_roles_user,
            **token_payload_one_group,
        }
    ],
    indirect=True,
)
async def test_user_posts_user(
    async_client: AsyncClient, app_override_get_azure_payload_dependency: FastAPI
):
    """Tests the post_user endpoint of the API."""
    app_override_get_azure_payload_dependency

    # Make a POST request to create the user
    response = await async_client.post(
        "/api/v1/user/",
        json=one_test_user,
    )

    assert response.status_code == 403
    assert response.text == '{"detail":"Access denied"}'

    # this would allow other users to create users, which is not allowed - only self-sign-up!:
    # assert response.status_code == 201
    # created_user = User(**response.json())
    # assert created_user.azure_user_id == one_test_user["azure_user_id"]
    # assert created_user.azure_tenant_id == one_test_user["azure_tenant_id"]

    # # Verify that the user was created in the database
    # async with UserCRUD() as crud:
    #     db_user = await crud.read_by_azure_user_id(one_test_user["azure_user_id"])
    # assert db_user is not None
    # db_user_json = jsonable_encoder(db_user)
    # assert "last_accessed_at" in db_user_json
    # assert db_user_json["azure_user_id"] == one_test_user["azure_user_id"]
    # assert db_user_json["azure_tenant_id"] == one_test_user["azure_tenant_id"]


## GET tests:


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_admin,
        }
    ],
    indirect=True,
)
async def test_admin_gets_users(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_one_test_user: User,
):
    """Test GET one user"""

    # mocks the access token:
    app_override_get_azure_payload_dependency

    # adds a user to the database, which is the one to GET:
    user = add_one_test_user

    response = await async_client.get("/api/v1/user/")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert "user_id" in users[0]
    assert users[0]["azure_user_id"] == str(user.azure_user_id)
    assert users[0]["azure_tenant_id"] == str(user.azure_tenant_id)


@pytest.mark.anyio
async def test_get_users_without_token(
    async_client: AsyncClient,
    add_one_test_user: User,
):
    """Test GET one user"""
    add_one_test_user

    response = await async_client.get("/api/v1/user/")
    assert response.status_code == 401
    assert response.text == '{"detail":"Invalid token"}'


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_user,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
        # here the admin get's itself => last_accessed_at should change!
        {
            **token_payload_scope_api_read,
            **token_payload_roles_admin,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
    ],
    indirect=True,
)
async def test_user_gets_user_by_azure_user_id(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_one_test_user_with_groups: UserRead,
):
    """Test a user GETs it's own user id from it's linked azure user account"""

    # mocks the access token:
    app_override_get_azure_payload_dependency
    user_in_database = add_one_test_user_with_groups

    response = await async_client.get(
        f"/api/v1/user/azure/{str(user_in_database.azure_user_id)}"
    )
    assert response.status_code == 200
    response_user = response.json()
    modelled_response_user = UserRead(**response_user)
    assert "user_id" in response_user
    assert response_user["azure_user_id"] == str(user_in_database.azure_user_id)
    assert response_user["azure_tenant_id"] == str(user_in_database.azure_tenant_id)
    # TBD: admin access should not change the last_accessed_at!
    assert modelled_response_user.last_accessed_at > user_in_database.last_accessed_at
    assert len(response_user["azure_groups"]) == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_admin,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
    ],
    indirect=True,
)
async def test_admin_gets_user_by_azure_user_id(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_many_test_users_with_groups: List[UserRead],
):
    """Test a user GETs it's own user id from it's linked azure user account"""

    # mocks the access token:
    app_override_get_azure_payload_dependency
    user_in_database = add_many_test_users_with_groups[1]

    response = await async_client.get(
        f"/api/v1/user/azure/{str(user_in_database.azure_user_id)}"
    )
    assert response.status_code == 200
    response_user = response.json()
    modelled_response_user = UserRead(**response_user)
    assert "user_id" in response_user
    assert response_user["azure_user_id"] == str(user_in_database.azure_user_id)
    assert response_user["azure_tenant_id"] == str(user_in_database.azure_tenant_id)
    assert modelled_response_user.last_accessed_at == user_in_database.last_accessed_at
    assert len(response_user["azure_groups"]) == 3


@pytest.mark.anyio
async def test_get_user_by_azure_id_without_token(
    async_client: AsyncClient,
    add_one_test_user: User,
):
    """Test GET one user"""
    user_in_db = add_one_test_user

    response = await async_client.get(
        f"/api/v1/user/azure/{str(user_in_db.azure_user_id)}"
    )
    assert response.status_code == 401
    assert response.text == '{"detail":"Invalid token"}'


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_user,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
        # here the admin get's itself => last_accessed_at should change!
        {
            **token_payload_scope_api_read,
            **token_payload_roles_admin,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
    ],
    indirect=True,
)
async def test_user_gets_user_by_id(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_one_test_user_with_groups: UserRead,
):
    """Test a user GETs it's own user by id"""

    # mocks the access token:
    app_override_get_azure_payload_dependency
    user_in_database = add_one_test_user_with_groups

    response = await async_client.get(f"/api/v1/user/{str(user_in_database.user_id)}")

    assert response.status_code == 200
    user = response.json()
    modelled_response_user = UserRead(**user)
    assert "user_id" in user
    assert user["azure_user_id"] == str(user_in_database.azure_user_id)
    assert user["azure_tenant_id"] == str(user_in_database.azure_tenant_id)
    # TBD: admin access should not change the last_accessed_at!
    assert modelled_response_user.last_accessed_at > user_in_database.last_accessed_at
    assert len(user["azure_groups"]) == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_admin,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
    ],
    indirect=True,
)
async def test_admin_gets_user_by_id(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_many_test_users_with_groups: List[UserRead],
):
    """Test a user GETs it's own user by id"""

    # mocks the access token:
    app_override_get_azure_payload_dependency

    user_in_database = add_many_test_users_with_groups[1]

    response = await async_client.get(f"/api/v1/user/{str(user_in_database.user_id)}")

    assert response.status_code == 200
    user = response.json()
    modelled_response_user = UserRead(**user)
    assert "user_id" in user
    assert user["azure_user_id"] == str(user_in_database.azure_user_id)
    assert user["azure_tenant_id"] == str(user_in_database.azure_tenant_id)
    # TBD: admin access should not change the last_accessed_at!
    assert modelled_response_user.last_accessed_at == user_in_database.last_accessed_at
    assert len(user["azure_groups"]) == 3


@pytest.mark.anyio
async def test_get_user_by_id_without_token(
    async_client: AsyncClient,
    add_one_test_user: User,
):
    """Test GET one user"""
    user_in_db = add_one_test_user

    response = await async_client.get(f"/api/v1/user/azure/{str(user_in_db.user_id)}")
    assert response.status_code == 401
    assert response.text == '{"detail":"Invalid token"}'


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            # missing scope_api_read
            **token_payload_roles_user,
            **token_payload_user_id,
            **token_payload_tenant_id,
        },
        # {
        #     ## Hmmm - user does not need to have a role to read itself
        #     # enabling this would mean that the all users need to be added in Azure Entra AD
        #     **token_payload_scope_api_read,
        #     # missing roles_user
        #     **token_payload_user_id,
        #     **token_payload_tenant_id,
        # },
    ],
    indirect=True,
)
async def test_get_user_by_id_with_missing_scope(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_one_test_user_with_groups: UserRead,
):
    """Test a user GETs it's own user by id"""

    # mocks the access token:
    app_override_get_azure_payload_dependency
    user_in_database = add_one_test_user_with_groups

    response = await async_client.get(f"/api/v1/user/{str(user_in_database.user_id)}")
    assert response.status_code == 403
    assert response.text == '{"detail":"Access denied"}'


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mocked_get_azure_token_payload",
    [
        {
            **token_payload_scope_api_read,
            **token_payload_roles_user,
            # missing user_id
            **token_payload_tenant_id,
        },
        {
            **token_payload_scope_api_read,
            **token_payload_roles_user,
            **token_payload_user_id,
            # missing tenant_id
        },
    ],
    indirect=True,
)
async def test_get_user_by_id_invalid_token(
    async_client: AsyncClient,
    app_override_get_azure_payload_dependency: FastAPI,
    add_one_test_user_with_groups: UserRead,
):
    """Test a user GETs it's own user by id"""

    # mocks the access token:
    app_override_get_azure_payload_dependency
    user_in_database = add_one_test_user_with_groups

    response = await async_client.get(f"/api/v1/user/{str(user_in_database.user_id)}")
    assert response.status_code == 401
    assert response.text == '{"detail":"Invalid token"}'


# Passing tests:
# ✔︎ admin user creates a user
# ✔︎ admin user reads all users
# ✔︎ admin user reads a user by azure id
# ✔︎ admin user reads a user by id
# ✔︎ regular user reads itself by azure_id
# ✔︎ regular user reads itself by id
# - admin user updates a user -> is_active is the only thing, that can get updated
# - admin user deletes a user
# - regular user deletes itself
# - last_accessed_at is updated on every create, read and update
# groups: groups are not part of the user endpoints - need their own endpoints, but security is taking care of the sign-up!
# - users connections to groups are created in the database
# - a user, that is already signed up was added in Azure to a new group: does the new connection show up in the database?

# Failing tests:
# - modify the user_id
# No token provided
# ✔︎ read all user
# ✔︎ read user by azure_id
# ✔︎ read user by id
# - update user
# - delete user
# Regular user (not admin):
# - wants to create another user
# - wants to read all user
# - wants to update a user
# - wants to read a different user by id
# - regular user wants to delete another user
