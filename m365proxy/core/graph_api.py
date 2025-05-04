"""Defines the Graph API client and decorators for API calls."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import logging
from m365proxy.helpers.graph_helper import graph_api, is_graph_available


@graph_api()
async def api_request(client, method, url, *args, **kwargs):
    """Make an async Graph API request using httpx.AsyncClient."""
    method = method.upper()
    if method not in ("GET", "POST", "DELETE", "PUT", "PATCH", "HEAD"):
        raise ValueError(f"Unsupported method: {method}")

    response = await client.request(method, url, *args, **kwargs)
    logging.debug(f"{method} {url} - [{response.status_code}]")
    logging.debug(f"Response: {response.text[:200]}...")
    return response
