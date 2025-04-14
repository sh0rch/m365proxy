import re
import socket
from pathlib import Path
from urllib.parse import unquote, quote
import logging

def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False
    
def is_file_writable(path: Path, confirm: bool = False) -> bool:
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
        with open(path, 'wb') as f:
            pass

    except Exception as e:
        logging.debug(f"Error checking {path.resolve()} file writability: {e}")
        return False
    
    return True

def is_file_readable(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        logging.debug(f"Path {path.resolve()} does not exist or is not a file.")
        return False
    try:
        with open(path, 'rb') as f:
            pass
        
    except Exception as e:
        logging.debug(f"Error checking {path.resolve()} file readability: {e}")
        return False

    return True

import re
from urllib.parse import unquote, quote

def parse_proxy_url(proxy_url: str,
                    user: str = None,
                    password: str = None,
                    default_scheme: str = "http",
                    default_port: int = None) -> str:
    
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

    auth_part = f"{user}:{password}@" if user and password else (f"{user}@" if user else "")
    port_part = f":{port}" if port else ""

    return f"{scheme}://{auth_part}{host}{port_part}"

def detect_prog():
    if __package__:
        return f"python -m {__package__}"
    elif sys.argv[0].endswith(".py"):
        return f"python {os.path.basename(sys.argv[0])}"
    else:
        return os.path.basename(sys.argv[0])
    
def get_app_data_dir(path: str = None) -> Path:
    if not path:
        path = Path.home() / ".m365proxy"
    else:
        path = Path(path).parent.resolve()

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise IOError(f"Cannot create application directory {path.resolve()}") from e
    return path.resolve()

def is_valid_email(email: str) -> bool:
    return bool(email and re.match(r"[^@]+@[^@]+\.[^@]+", email))

def is_port_available(host, port, timeout=2.0):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result != 0

def validated_input(prompt: str, validation_func: any, default = None) -> str:
    if default:
        prompt += f" (default: {str(default)})"

    while True:
        user_input = input(prompt + ": ").strip()

        if not user_input and default:
            return default
        
        if not user_input or not validation_func(user_input):
            print(f"Invalid input. Please try again.")
            continue
        
        return user_input
    
def sanitize_url(url: str) -> str:
    return re.sub(
        r'(?P<scheme>\w+://)(?P<user>[^:@/\s]+):(?P<password>[^@/\s]+)@',
        r'\g<scheme>\g<user>:****@',
        url
    )
