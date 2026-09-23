"""Initialize an ha-lite installation and issue access tokens from the shell.

ha-lite has no onboarding, which is where Home Assistant creates its first
user. This script does that headlessly, and issues the long-lived access tokens
machine clients such as MCP agents authenticate with.

    hass --script owner -c CONFIG create --name NAME --username USERNAME
    hass --script owner -c CONFIG token --client-name NAME

Run it while ha-lite is stopped: it writes the auth store directly.
"""

import argparse
import asyncio
from collections.abc import Sequence
from datetime import timedelta
import getpass
import logging
import os

from homeassistant import runner
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
from homeassistant.auth.providers import homeassistant as hass_auth
from homeassistant.config import get_default_config_dir
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

DEFAULT_TOKEN_LIFESPAN_DAYS = 3650


def run(args: Sequence[str] | None) -> int:
    """Handle the owner script."""
    parser = argparse.ArgumentParser(
        description="Create the owner and issue access tokens"
    )
    parser.add_argument("--script", choices=["owner"])
    parser.add_argument(
        "-c",
        "--config",
        default=get_default_config_dir(),
        help="Directory that contains the Home Assistant configuration",
    )

    subparsers = parser.add_subparsers(dest="func")
    subparsers.required = True

    parser_create = subparsers.add_parser(
        "create", help="Create the owner, the first administrator"
    )
    parser_create.add_argument("--name", required=True)
    parser_create.add_argument("--username", required=True)
    parser_create.add_argument(
        "--password", help="Prompted for when omitted, so it stays out of history"
    )
    parser_create.set_defaults(func=create_owner)

    parser_token = subparsers.add_parser(
        "token", help="Issue a long-lived access token for the owner"
    )
    parser_token.add_argument("--client-name", required=True)
    parser_token.add_argument(
        "--lifespan", type=int, default=DEFAULT_TOKEN_LIFESPAN_DAYS, help="In days"
    )
    parser_token.set_defaults(func=create_token)

    return asyncio.run(
        run_command(parser.parse_args(args)), loop_factory=runner.create_event_loop
    )


async def run_command(args: argparse.Namespace) -> int:
    """Run the command against the auth store of the configuration."""
    hass = HomeAssistant(os.path.join(os.getcwd(), args.config))
    hass.config_entries = ConfigEntries(hass, {})
    # The device registry migration waits for the config entries to load
    await hass.config_entries.async_initialize()
    dr.async_setup(hass)
    await asyncio.gather(dr.async_load(hass), er.async_load(hass))
    hass.auth = await auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    provider = hass.auth.auth_providers[0]
    await provider.async_initialize()
    result: int = await args.func(hass, provider, args)

    # The instance never started, so only a forced stop runs the final write
    # that flushes the auth store's delayed save.
    logging.getLogger("homeassistant.core").setLevel(logging.WARNING)
    await hass.async_stop(force=True)
    return result


async def create_owner(
    hass: HomeAssistant, provider: hass_auth.HassAuthProvider, args: argparse.Namespace
) -> int:
    """Create the owner with username/password credentials."""
    # The first user that is not system generated becomes the owner, so any
    # such user means the installation is already initialized.
    if any(not user.system_generated for user in await hass.auth.async_get_users()):
        print("Already initialized: a user exists")
        return 1

    password = args.password or getpass.getpass("Password: ")
    try:
        await provider.async_add_auth(args.username, password)
    except hass_auth.InvalidUsername as err:
        print(f"Invalid username: {err}")
        return 1
    assert provider.data is not None
    await provider.data.async_save()

    user = await hass.auth.async_create_user(args.name, group_ids=[GROUP_ID_ADMIN])
    credentials = await provider.async_get_or_create_credentials(
        {"username": args.username}
    )
    await hass.auth.async_link_user(user, credentials)
    print(f"Owner created: {user.name}")
    return 0


async def create_token(
    hass: HomeAssistant, provider: hass_auth.HassAuthProvider, args: argparse.Namespace
) -> int:
    """Print a new long-lived access token for the owner."""
    if (owner := await hass.auth.async_get_owner()) is None:
        print("No owner yet: run the create command first")
        return 1

    try:
        refresh_token = await hass.auth.async_create_refresh_token(
            owner,
            client_name=args.client_name,
            token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
            access_token_expiration=timedelta(days=args.lifespan),
        )
    except ValueError as err:
        print(err)
        return 1

    print(hass.auth.async_create_access_token(refresh_token))
    return 0
