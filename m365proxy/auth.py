# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import sys
import json
import logging
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta, timezone
from base64 import urlsafe_b64encode, urlsafe_b64decode
from hashlib import sha256
from cryptography.fernet import Fernet
from msal import PublicClientApplication
from m365proxy.config import get_config_value
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
AUTHORITY = "https://login.microsoftonline.com"
SCOPES=[
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/Mail.Send.Shared",
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/Mail.ReadWrite.Shared",
        "https://graph.microsoft.com/User.Read"
    ]

def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs}s" if hours > 0 else f"{minutes}m {secs}s" if minutes > 0 else f"{secs}s"

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode(), salt)
    return hashed.decode()

def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def load_tokens() -> Optional[dict]:
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
    part = get_config_value("client_id").split("-")[-1]
    return urlsafe_b64encode(sha256(part.encode()).digest())

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def refresh_token_if_needed(force=False) -> bool:
    tokens = load_tokens()
    if not tokens:
        logging.error("No token found or unable to decrypt.")
        return False
    
    last = tokens.get("last_refresh")
    if last:
        try:
            last = datetime.fromisoformat(last)
        except Exception:
            last = datetime(1970, 1, 1).replace(tzinfo=timezone.utc) 
    else:
        last = datetime(1970, 1, 1).replace(tzinfo=timezone.utc)

    if "refresh_token" in tokens and not force and datetime.now(timezone.utc) - last < timedelta(hours=1):
        return True

    if "refresh_token" not in tokens:
        logging.error("Refresh token not found. Please login using device_code flow.")
        return False

    app = PublicClientApplication(get_config_value("client_id"), authority=f"{AUTHORITY}/{get_config_value('tenant_id')}")
    result = app.acquire_token_by_refresh_token(tokens["refresh_token"], scopes=SCOPES)
    if "access_token" in result:
        result["last_refresh"] = now_utc_iso()
        if save_tokens(result):
            logging.info("Refresh token saved successfully.")
            return True
    
    return False

async def get_access_token() -> Optional[str]:
    await refresh_token_if_needed()
    tokens = load_tokens()
    if not tokens or "access_token" not in tokens:
        logging.error("Access token not found. Please login using device_code flow.")
        return None
    return tokens["access_token"]

async def interactive_login() -> bool:

    app = PublicClientApplication(get_config_value("client_id"), authority=f"{AUTHORITY}/{get_config_value('tenant_id')}")
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])
    
    result = app.acquire_token_by_device_flow(flow)

    try:
        parts = result["access_token"].split(".")
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = json.loads(urlsafe_b64decode(padded.encode()))
        scopes = decoded.get("scp", "").split()
        required = {"Mail.Send", "Mail.Send.Shared", "Mail.ReadWrite", "Mail.ReadWrite.Shared"}
        if not required.issubset(set(scopes)):
            print("Access token is missing required scopes: Mail.Send, Mail.Send.Shared, Mail.ReadWrite, Mail.ReadWrite.Shared", file=sys.stderr)
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
    tokens = load_tokens()
    if not tokens:
        print("No token found or unable to decrypt.", file=sys.stderr)
        return False

    print("🔐 Decrypted token data:")
    if "expires_in" in tokens:
        try:
            tokens["expires_in_human"] = format_duration(int(tokens["expires_in"]))
        except:
            pass
        
    print(json.dumps(tokens, indent=2))
    return True

def check_credentials(username: str, password: str) -> bool:
    for mailbox in get_config_value("mailboxes", []):
        if mailbox.get("username") == username and check_password(password, mailbox.get("password", "")):
            logging.info(f"Credentials for {username} are valid.")
            return True
    logging.warning(f"Credentials for {username} are invalid.")
    return False
