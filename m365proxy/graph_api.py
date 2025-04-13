# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import functools
import logging
import requests
import os

from m365proxy.auth import get_access_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
PROXIES = {"https": HTTPS_PROXY} if HTTPS_PROXY else None
DEFAULT_TIMEOUT = 10

def get_auth_headers(token: str, **kwargs) -> dict:
    headers = kwargs.get("headers", {})
    headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    kwargs["headers"] = headers
    kwargs.setdefault("proxies", PROXIES)
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return kwargs

def request_func(method: str):
    request_map = {
        'GET': requests.get,
        'POST': requests.post,
        'DELETE': requests.delete,
        'RAW': requests.get
    }
    if method.upper() not in request_map:
        raise ValueError(f"Unsupported method: {method}")
    return request_map[method.upper()]

def handle_graph_exception(exc: Exception, is_async: bool = False):
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if hasattr(exc, "response") else getattr(exc, "status", None)
        text = exc.response.text if hasattr(exc, "response") else getattr(exc, "message", str(exc))
        logging.error(f"Graph API error: {status} - {text}")
    else:
        logging.error(f"Graph API call failed. {exc.__class__.__name__}, {exc.response}: {exc}")



def graph_api():
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(method, url, *args, **kwargs):
            try:
                logging.debug(f"Calling {func.__name__} with token (async)")
                token = await get_access_token()
                kwargs = get_auth_headers(token, **kwargs)
                url = url if "://" in url else f"{GRAPH_BASE}{url}"
                result = await func(method, url, *args, **kwargs)
                return result

            except Exception as e:
                handle_graph_exception(e, is_async=True)
                return None
        return async_wrapper
    return decorator

@graph_api()
async def api_request(method, url, *args, **kwargs):
    request_map = {
        'GET': requests.get,
        'POST': requests.post,
        'DELETE': requests.delete,
        'RAW': requests.get
    }
    if method.upper() not in request_map:
        raise ValueError(f"Unsupported method: {method}")
    method = 'GET' if method.upper() == 'RAW' else method.upper()
    r = requests.request(method, url, *args, **kwargs)
    logging.debug(f"Request: {method} {url} - [{r.status_code}]")
    #r.raise_for_status()
    if method == 'RAW':
        logging.debug(f"GET RAW {url} - [{r.status_code}]: {r.content[:100]}...")
    else:
        logging.debug(f"{method} {url} - [{r.status_code}]: {r.text[:100]}...")
    return r
