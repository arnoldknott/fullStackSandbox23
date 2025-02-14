import asyncio
from typing import List
from unittest.mock import patch

import pytest
import socketio
import uvicorn


@pytest.fixture(scope="function")
async def mock_token_payload(request):
    """Returns a mocked token payload."""

    # print("=== mock_token_payload ===")
    # print(request.param)

    with patch("core.security.decode_token") as mock:
        mock.return_value = request.param
        # yield mock
        yield request.param
    # return request.param


@pytest.fixture(scope="function")
async def mock_get_user_account_from_session_cache():
    """Returns a mocked token."""

    with patch("core.security.get_user_account_from_session_cache") as mock:
        mock.return_value = {
            "userName": "testuser",
            "homeAccountId": "testhometenantid.testhomeaccounid",
        }
        yield mock


@pytest.fixture(scope="function")
async def mock_get_azure_token_from_cache():
    """Returns a mocked token."""

    with patch("core.security.get_azure_token_from_cache") as mock:
        mock.return_value = "ey-fake-token-from_cache"
        yield mock


@pytest.fixture()
async def socketio_test_server(
    mock_token_payload,
    mock_get_azure_token_from_cache,
    mock_get_user_account_from_session_cache,
):
    """Provide a socket.io server."""
    mock_token_payload

    sio = socketio.AsyncServer(async_mode="asgi", logger=True, engineio_logger=True)
    app = socketio.ASGIApp(sio, socketio_path="socketio/v1")

    config = uvicorn.Config(app, host="127.0.0.1", port=8669, log_level="info")
    server = uvicorn.Server(config)

    asyncio.create_task(server.serve())
    await asyncio.sleep(1)
    yield sio
    await server.shutdown()


# This one connects to a socketio server in FastAPI:
# host="http://127.0.0.1:80" => production server
# host="http://127.0.0.1:8669" => test server from fixture socketio_test_server
@pytest.fixture
async def socketio_test_client():
    """Provides a socket.io client and connects to it."""

    async def _socketio_test_client(
        namespaces: List[str] = None, server_host: str = "http://127.0.0.1:8669"
    ):
        client = socketio.AsyncClient(logger=True, engineio_logger=True)

        if server_host == "http://127.0.0.1:8669":
            socketio_test_server

        await client.connect(
            server_host,
            socketio_path="socketio/v1",
            namespaces=namespaces,
            auth={"session_id": "testsessionid"},
        )
        yield client
        await client.disconnect()

    return _socketio_test_client
