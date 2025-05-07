"""Authentication and token management for Microsoft 365 and m365proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import json
import logging
import sys
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Optional
import httpx
import bcrypt
from cryptography.fernet import Fernet
from msal import PublicClientApplication

from m365proxy.config import get_config_value


AUTHORITY = "https://login.microsoftonline.com"
# TOKEN_URL = f"{AUTHORITY}/{get_config_value('tenant_id')}/oauth2/v2.0/token"
BASE_DIR = Path(__file__).resolve().parent
SCOPES = [
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Mail.Send.Shared",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.ReadWrite.Shared",
    "https://graph.microsoft.com/User.Read"
]


def get_token_url() -> str:
    """Get the token URL for Microsoft Graph API."""
    return f"{AUTHORITY}/{get_config_value('tenant_id')}/oauth2/v2.0/token"


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs}s" if hours > 0 else \
        f"{minutes}m {secs}s" if minutes > 0 else f"{secs}s"


def hash_password(plain_password: str) -> str:
    """Hash a plain password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode(), salt)
    return hashed.decode()


def check_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain password matches a hashed password."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def load_tokens() -> Optional[dict]:
    """Load tokens from the specified token path."""
    token_path = Path(get_config_value("token_path"))
    if not token_path.exists():
        return None
    part = get_key_part()
    fernet = Fernet(part)
    try:
        return json.loads(fernet.decrypt(token_path.read_bytes()).decode())
    except Exception:
        return None


def save_tokens(data: dict) -> bool:
    """Save tokens to the specified token path."""
    token_path = Path(get_config_value("token_path"))
    try:
        part = get_key_part()
        fernet = Fernet(part)
        token_path.write_bytes(fernet.encrypt(json.dumps(data).encode()))
    except Exception as e:
        logging.error(f"Failed to save tokens: {e}")
        return False
    return True


def get_key_part() -> bytes:
    """Generate a key part for encryption/decryption."""
    part = get_config_value("client_id").split("-")[-1]
    return urlsafe_b64encode(sha256(part.encode()).digest())


def now_utc_iso() -> str:
    """Get the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


async def refresh_token_if_needed(force=False) -> bool:
    """Refresh the access token if needed, using httpx."""
    tokens = load_tokens()
    if not tokens:
        logging.error("No token found or unable to decrypt.")
        return False

    last = tokens.get("last_refresh")
    try:
        last = datetime.fromisoformat(last) if last else datetime(
            1970, 1, 1, tzinfo=timezone.utc)
    except Exception:
        last = datetime(1970, 1, 1, tzinfo=timezone.utc)

    if "refresh_token" not in tokens:
        logging.error(
            "Refresh token not found. Please login using device_code flow.")
        return False

    if not force and (datetime.now(timezone.utc) - last) < timedelta(hours=1):
        return True  # Токен ещё валиден

    data = {
        "client_id": get_config_value("client_id"),
        "scope": " ".join(SCOPES),
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(get_token_url(), data=data)
            response.raise_for_status()
            result = response.json()
    except httpx.RequestError as e:
        logging.error(f"HTTP error during token refresh: {e}")
        return False
    except httpx.HTTPStatusError as e:
        logging.error(
            f"Graph token refresh failed: {e.response.status_code} {e.response.text}")
        return False

    if "access_token" in result:
        result["last_refresh"] = now_utc_iso()
        if save_tokens(result):
            logging.info("Refresh token saved successfully.")
            return True
        else:
            logging.error("Failed to save refreshed token.")
    else:
        logging.error("No access token returned in response.")
    return False


async def get_access_token() -> Optional[str]:
    """Ensure access token is fresh and return it."""
    await refresh_token_if_needed()
    tokens = load_tokens()
    if not tokens or "access_token" not in tokens:
        logging.error(
            "Access token not found. Please login using device_code flow.")
        return None
    return tokens["access_token"]


async def interactive_login() -> bool:
    """Perform interactive login using device_code flow."""
    app = PublicClientApplication(
        get_config_value("client_id"),
        authority=f"{AUTHORITY}/{get_config_value('tenant_id')}"
    )
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])

    result = app.acquire_token_by_device_flow(flow)

    try:
        parts = result["access_token"].split(".")
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = json.loads(urlsafe_b64decode(padded.encode()))
        scopes = decoded.get("scp", "").split()
        required = {
            "Mail.Send",
            "Mail.Send.Shared",
            "Mail.ReadWrite",
            "Mail.ReadWrite.Shared"
        }
        if not required.issubset(set(scopes)):
            print("Access token is missing required scopes: Mail.Send,"
                  " Mail.Send.Shared, Mail.ReadWrite, Mail.ReadWrite.Shared",
                  file=sys.stderr)
            return False
    except Exception as e:
        print(f"Failed to decode token: {e}", file=sys.stderr)
        return False

    if "access_token" in result:
        result["last_refresh"] = now_utc_iso()
        save_tokens(result)
        print("Login successful and token saved.")
    else:
        print("Login failed.", file=sys.stderr)
        return False

    return True


def show_tokens() -> bool:
    """Display the decrypted token data."""
    tokens = load_tokens()
    if not tokens:
        print("No token found or unable to decrypt.", file=sys.stderr)
        return False

    print("Decrypted token data:")
    if "expires_in" in tokens:
        try:
            tokens["expires_in_human"] = format_duration(
                int(tokens["expires_in"]))
        except (KeyError, ValueError, TypeError):
            pass

    print(json.dumps(tokens, indent=2))
    return True


def check_credentials(username: str, password: str) -> bool:
    """Check if the provided credentials are valid."""
    for mailbox in get_config_value("mailboxes", []):
        if mailbox.get("username") == username and \
                check_password(password, mailbox.get("password", "")):
            logging.info(f"Credentials for {username} are valid.")
            return True
    logging.warning(f"Credentials for {username} are invalid.")
    return False
