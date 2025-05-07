"""Graph API helper module for m365proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import os
import asyncio
import logging
import httpx
from functools import wraps
from m365proxy.auth import get_access_token


GRAPH_HOST = "graph.microsoft.com"
GRAPH_BASE = f"https://{GRAPH_HOST}/v1.0"
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
DEFAULT_TIMEOUT = 10.0


def get_httpx_proxies() -> str | None:
    """Return proxy URL if HTTPS_PROXY is set."""
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if proxy_url:
        return proxy_url
    return None


async def is_graph_reachable(timeout=1.0):
    """Check if the Graph API is reachable."""
    proxy = get_httpx_proxies()
    try:
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
            response = await client.head(f"{GRAPH_BASE}/me")
            if response.status_code in (200, 401, 403):
                return True
            if response.status_code == 405:
                logging.debug(
                    "Graph responded — still reachable")
                return True
            return False
    except httpx.RequestError as e:
        logging.debug(
            f"Graph reachability check failed: {type(e).__name__}: {e}")
        return False


async def is_dns_available(host=GRAPH_HOST) -> bool:
    """Check if DNS is available for the given host."""
    try:
        loop = asyncio.get_running_loop()
        await loop.getaddrinfo(host, None)
        return True
    except Exception as e:
        logging.debug(f"DNS resolution failed: {e}")
        return False


async def is_graph_available():
    """Check if the Graph API is available."""
    return await is_dns_available() and await is_graph_reachable(timeout=1.0)


def get_auth_headers(token: str, extra_headers: dict = None) -> dict:
    """Forms headers for authorization."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def handle_graph_exception(exc: Exception):
    """Handle errors from the Graph API."""
    if isinstance(exc, httpx.HTTPStatusError):
        logging.error(f"Graph API HTTP error: {exc.response.status_code}"
                      f" - {exc.response.text}")
    elif isinstance(exc, httpx.RequestError):
        logging.error(f"Graph API request error: {exc}")
    else:
        logging.error(f"Graph API unknown error: {exc}")


def graph_api():
    """Wrap Microsoft Graph API calls."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(method, url, *args, **kwargs):
            proxy = get_httpx_proxies()
            try:
                logging.debug(f"Calling {func.__name__} with token (async)")
                token = await get_access_token()
                headers = get_auth_headers(token)
                url = url if "://" in url else f"{GRAPH_BASE}{url}"
                async with httpx.AsyncClient(
                    proxy=proxy,
                    timeout=DEFAULT_TIMEOUT
                ) as client:
                    kwargs.setdefault("headers", headers)
                    response = await func(client, method, url, *args, **kwargs)
                    response.raise_for_status()
                    return response
            except Exception as e:
                handle_graph_exception(e)
                return None
        return async_wrapper
    return decorator


def safe_graph_api_request(fallback=None):
    """Check network unavailability for the Graph API."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await is_graph_available():
                logging.warning("Graph API not reachable — fast check failed")
                if callable(fallback):
                    return fallback(*args, **kwargs)
                return fallback
            try:
                return await func(*args, **kwargs)
            except httpx.RequestError as e:
                logging.warning(
                    f"Graph API unavailable — {type(e).__name__}: {e}")
                if callable(fallback):
                    return fallback(*args, **kwargs)
                return fallback
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                reason = e.response.reason_phrase
                logging.warning(f"Graph API HTTP error: {status} {reason}")
                if status in (502, 503, 504):
                    if callable(fallback):
                        return fallback(*args, **kwargs)
                    return fallback
                raise
            except Exception as e:
                logging.error(
                    "Unexpected error during Graph API call:"
                    f" {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator
