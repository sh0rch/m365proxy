"""Refresh access token background task."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import logging

from m365proxy.auth import refresh_token_if_needed
from m365proxy.utils.shutdown import trigger_shutdown
from m365proxy.helpers import is_graph_available


async def background_token_refresh(shutdown_event: asyncio.Event) -> None:
    """Background task to refresh the access token every 3 days."""
    try:
        while not shutdown_event.is_set():
            if not await is_graph_available():
                logging.warning("Graph API is unreachable. "
                                "Will retry in 15 minutes.")
                await asyncio.sleep(15 * 60)
                continue

            success = await refresh_token_if_needed()
            if not success:
                logging.error(
                    "Token renewal failed. Shutting down.")
                trigger_shutdown(shutdown_event)
                break

            logging.info("Token refreshed. Sleeping for 3 days.")
            await asyncio.sleep(3 * 24 * 60 * 60)

    except asyncio.CancelledError:
        logging.info("Background token refresh cancelled.")
