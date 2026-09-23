"""Test the owner script that initializes ha-lite without onboarding."""

from argparse import Namespace
import asyncio
from collections.abc import Generator
import json
import logging
from pathlib import Path

import pytest

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
from homeassistant.auth.providers import homeassistant as hass_auth
from homeassistant.core import HomeAssistant
from homeassistant.scripts import owner as script_owner

from tests.common import register_auth_provider


@pytest.fixture(autouse=True)
def reset_log_level() -> Generator[None]:
    """Reset log level after each test case."""
    logger = logging.getLogger("homeassistant.core")
    orig_level = logger.level
    yield
    logger.setLevel(orig_level)


@pytest.fixture
async def provider(hass: HomeAssistant) -> hass_auth.HassAuthProvider:
    """Home Assistant auth provider."""
    provider = await register_auth_provider(hass, {"type": "homeassistant"})
    await provider.async_initialize()
    return provider


async def test_create_owner(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The first user becomes the owner, an admin with login credentials."""
    result = await script_owner.create_owner(
        hass, provider, Namespace(name="Admin", username="admin", password="secret")
    )

    assert result == 0
    assert capsys.readouterr().out == "Owner created: Admin\n"
    owner = await hass.auth.async_get_owner()
    assert owner is not None
    assert [group.id for group in owner.groups] == [GROUP_ID_ADMIN]
    assert [cred.data["username"] for cred in owner.credentials] == ["admin"]
    assert provider.data is not None
    provider.data.validate_login("admin", "secret")


async def test_create_owner_refuses_an_initialized_installation(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A second run must not create a second, non-owner administrator."""
    await hass.auth.async_create_user("Existing")

    result = await script_owner.create_owner(
        hass, provider, Namespace(name="Admin", username="admin", password="secret")
    )

    assert result == 1
    assert capsys.readouterr().out == "Already initialized: a user exists\n"


async def test_create_owner_rejects_an_invalid_username(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An invalid username leaves no user behind."""
    result = await script_owner.create_owner(
        hass, provider, Namespace(name="Admin", username=" admin ", password="secret")
    )

    assert result == 1
    assert capsys.readouterr().out.startswith("Invalid username:")
    assert await hass.auth.async_get_users() == []


async def test_create_token(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The printed token authenticates as the owner."""
    await script_owner.create_owner(
        hass, provider, Namespace(name="Admin", username="admin", password="secret")
    )
    capsys.readouterr()

    result = await script_owner.create_token(
        hass, provider, Namespace(client_name="agent", lifespan=30)
    )

    assert result == 0
    refresh_token = hass.auth.async_validate_access_token(
        capsys.readouterr().out.strip()
    )
    assert refresh_token is not None
    assert refresh_token.user == await hass.auth.async_get_owner()
    assert refresh_token.token_type == TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
    assert refresh_token.client_name == "agent"


async def test_create_token_needs_an_owner(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without an owner there is nobody to issue a token for."""
    result = await script_owner.create_token(
        hass, provider, Namespace(client_name="agent", lifespan=30)
    )

    assert result == 1
    assert capsys.readouterr().out == "No owner yet: run the create command first\n"


async def test_create_token_rejects_a_duplicate_client_name(
    hass: HomeAssistant,
    provider: hass_auth.HassAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Long-lived tokens are told apart by client name."""
    await script_owner.create_owner(
        hass, provider, Namespace(name="Admin", username="admin", password="secret")
    )
    await script_owner.create_token(
        hass, provider, Namespace(client_name="agent", lifespan=30)
    )
    capsys.readouterr()

    result = await script_owner.create_token(
        hass, provider, Namespace(client_name="agent", lifespan=30)
    )

    assert result == 1
    assert "agent already exists" in capsys.readouterr().out


async def test_run_persists_the_owner_and_the_token(tmp_path: Path) -> None:
    """Both commands write the auth store of a configuration that never ran.

    The instance the script creates is never started, and a plain stop of an
    instance that never started skips the final write, which would silently
    lose the owner.
    """
    config_dir = str(tmp_path)
    event_loop = asyncio.get_running_loop()

    assert (
        await event_loop.run_in_executor(
            None,
            script_owner.run,
            [
                "-c",
                config_dir,
                "create",
                "--name",
                "Admin",
                "--username",
                "admin",
                "--password",
                "secret",
            ],
        )
        == 0
    )
    assert (
        await event_loop.run_in_executor(
            None, script_owner.run, ["-c", config_dir, "token", "--client-name", "a"]
        )
        == 0
    )

    auth = json.loads((tmp_path / ".storage" / "auth").read_text())["data"]
    assert [(user["name"], user["is_owner"]) for user in auth["users"]] == [
        ("Admin", True)
    ]
    assert [token["client_name"] for token in auth["refresh_tokens"]] == ["a"]
