"""Utility functions for m365proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import logging
import re
import socket
from pathlib import Path
from urllib.parse import quote, unquote


def is_integer(value):
    """Check if the value is an integer."""
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_file_writable(path: Path, confirm: bool = False) -> bool:
    """Check if the file is writable."""
    if path.is_dir():
        logging.debug(f"Path {path.resolve()} is a directory, not a file.")
        return False

    if path.exists() and confirm:
        print(f"{path.resolve()} file already exists!")
        confirm = input("Do you want to overwrite it? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return False

    try:
        with open(path, 'wb'):
            pass

    except Exception as e:
        logging.debug(f"Error checking {path.resolve()} file writability: {e}")
        return False

    return True


def is_file_readable(path: Path) -> bool:
    """Check if the file is readable."""
    if not path.exists() or not path.is_file():
        logging.debug(
            f"Path {path.resolve()} does not exist or is not a file.")
        return False
    try:
        with open(path, 'rb'):
            pass

    except Exception as e:
        logging.debug(f"Error checking {path.resolve()} file readability: {e}")
        return False

    return True


def parse_proxy_url(proxy_url: str,
                    user: str = None,
                    password: str = None,
                    default_scheme: str = "http",
                    default_port: int = None) -> str:
    """Parse a proxy URL and return its components."""
    regex = re.compile(
        r'^(?:(?P<scheme>\w+)://)?'
        r'(?:(?P<user>[^:@]+)(?::(?P<password>[^@]+))?@)?'
        r'(?P<host>[^:]+)'
        r'(?::(?P<port>\d+))?$'
    )

    match = regex.match(proxy_url)

    if not match:
        return ""

    parts = match.groupdict()

    scheme = parts['scheme'] if parts['scheme'] else default_scheme

    user = user if user else parts['user']
    password = password if password else parts['password']
    host = parts['host']
    port = parts['port'] if parts['port'] else default_port

    if password:
        password = quote(unquote(password))

    auth_part = f"{user}:{password}@" if user and password else (
        f"{user}@" if user else "")
    port_part = f":{port}" if port else ""

    return f"{scheme}://{auth_part}{host}{port_part}"


def detect_prog():
    """Detect the program name."""
    import os
    import sys

    if __package__:
        return f"python -m {__package__}"
    elif sys.argv[0].endswith(".py"):
        return f"python {os.path.basename(sys.argv[0])}"
    else:
        return os.path.basename(sys.argv[0])


def get_app_data_dir(path: str = None) -> Path:
    """Get the application data directory."""
    if not path:
        path = Path.home() / ".m365proxy"
    else:
        path = Path(path).parent.resolve()

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise IOError(
            f"Cannot create application directory {path.resolve()}") from e
    return path.resolve()


def is_valid_email(email: str) -> bool:
    """Check if the email address is valid."""
    return bool(email and re.match(r"[^@]+@[^@]+\.[^@]+", email))


def is_port_available(host, port, timeout=2.0):
    """Check if the port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result != 0


def validated_input(prompt: str, validation_func: any, default=None) -> str:
    """Get user input with validation."""
    if default:
        prompt += f" (default: {str(default)})"

    while True:
        user_input = input(prompt + ": ").strip()

        if not user_input and default:
            return default

        if not user_input or not validation_func(user_input):
            print("Invalid input. Please try again.")
            continue

        return user_input


def sanitize_url(url: str) -> str:
    """Sanitize the URL by masking the password."""
    return re.sub(
        r'(?P<scheme>\w+://)(?P<user>[^:@/\s]+):(?P<password>[^@/\s]+)@',
        r'\g<scheme>\g<user>:****@',
        url
    )
