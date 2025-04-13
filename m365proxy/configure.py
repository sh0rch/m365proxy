# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import json
import sys
from pathlib import Path
from m365proxy.auth import hash_password
from m365proxy.utils import (
    is_file_writable,
    is_valid_email,
    is_integer,
    validated_input
)

DEFAULT_CONFIG = {
    "user": "user@example.com",
    "client_id": "xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "tenant_id": "yyyyyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "smtp_port": 10025,
    "pop3_port": None,
    "allowed_domains": ["*"],
    "mailboxes": [
        {
            "username": "send_as@example.com",
            "password": "secret123"
        }
    ],
    "logging": {
        "log_level": "INFO",
        "log_file": "m365.log"
    },
    "token_path": "tokens.enc"
}
    
def init_config(config_path: str) -> bool:
    config_path = Path(config_path)

    if not is_file_writable(config_path, confirm=True):
        return False
    
    DEFAULT_CONFIG["logging"]["log_file"] = str(config_path.parent.resolve() / "m365.log")
    DEFAULT_CONFIG["token_path"] = str(config_path.parent.resolve() / "token.enc")

    try:
        with open(config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    except IOError as e:
        print(f"Error writing to config file: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    
    print(f"Default configuration written to: {config_path.resolve()}")
    print("Please review and complete the configuration file before running the proxy.")
    return True

def interactive_configure(config_path: str):
    config_path = Path(config_path)
    
    if not is_file_writable(config_path, confirm=True):
        return False
  
    config_folder = config_path.parent
    
    try:
        print("Let's configure your M365 Proxy!")
        user = validated_input("Enter main user (e.g. user@example.com): ", is_valid_email).strip()
        client_id = input("Enter Azure client_id: ").strip()
        tenant_id = input("Enter Azure tenant_id: ").strip()
        
        smtp_port = validated_input("Enter SMTP port (default 10025): ", is_integer, 10025)
        pop3 = input("Enable inbound mail (POP3)? [y/N]: ").strip().lower() == "y"
        if pop3:
            pop3_port = validated_input("  Enter POP3 port (default 10110): ", is_integer,10110)
        else:
            pop3_port = None

        print("Configure allowed recipient domains")
        raw_domains = input("  Allowed domains (comma-separated, e.g. example.com, contoso.com or * to allow all domains): ").strip()
        allowed_domains = [d.strip().lower() for d in raw_domains.split(",") if d.strip()]
        if "*" in allowed_domains:
            allowed_domains = ["*"]
            
        mailboxes = []
        while True:
            print("Add mailbox (used for sending or receiving):")
            mbx_user = validated_input("  Mailbox username (e.g. send_as@example.com): ", is_valid_email).strip()
            mbx_pass = input("  Mailbox password: ").strip()
            mailboxes.append({
                "username": mbx_user,
                "password": hash_password(mbx_pass)
            })
            more = input("Add another mailbox? [y/N]: ").strip().lower()
            if more != "y":
                break

        print("")
        print("[Optional]: Configure HTTPS proxy")
        proxy_url = input("  Proxy address (e.g. proxy.local:3128 or http://proxy.local:3128) [leave blank to skip]: ").strip()
        https_proxy = None
        if proxy_url:
            if "://" not in proxy_url:
                proxy_url = "http://" + proxy_url

            proxy_user = input("  Proxy username [optional]: ").strip()
            proxy_pass = input("  Proxy password [optional]: ").strip()
            https_proxy = {"url": proxy_url}
            if proxy_user:
                https_proxy["username"] = proxy_user
            if proxy_pass:
                https_proxy["password"] = proxy_pass
        
        enable_tls = input("[Optional]: Enable STARTTLS (or POP3S)? [y/N]: ").strip().lower() == "y"
        tls_config = None
        if enable_tls:
            tls_cert = Path(config_folder / 'cert.pem').resolve()
            tls_cert = input(f"  [Optional]: Path to TLS certificate file (default: \"{tls_cert}\"):: ").strip() or tls_cert
            tls_key = Path(config_folder / 'cert_key.pem').resolve()
            tls_key = input(f"  [Optional]: Path to TLS private key file (default: \"{tls_key}\"):: ").strip() or tls_key
            tls_config = {
                "tls_cert": str(tls_cert),
                "tls_key": str(tls_key)
            }
        
        log_file = Path(config_folder / 'm365.log').resolve()
        log_level = input("[Optional]: Set log level (default INFO, allowed levels: DEBUG, INFO, WARNING, ERROR): ").strip() or "INFO"
        if log_level and log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            print("Invalid log level. Defaulting to INFO.")
            log_level = "INFO"

        log_file = input(f"  [Optional]: Log file path (default: \"{log_file}\"): ").strip() or log_file
        log_config = {
            "log_level": log_level,
            "log_file": str(log_file)
        }

        result = {
            "user": user,
            "client_id": client_id,
            "tenant_id": tenant_id,
            "allowed_domains": allowed_domains,
            "mailboxes": mailboxes,
            "bind": "127.0.0.1",
            "smtp_port": smtp_port,
            "pop3_port": pop3_port,
            "logging": log_config,
            "token_path": str(config_folder / "tokens.enc"),
        }

        if https_proxy:
            result["https_proxy"] = https_proxy

        if tls_config:
            result["tls"] = tls_config
    
        print(f"New configuration:")
        print(json.dumps(result, indent=4))
        
        with open(config_path, "w") as f:
            json.dump(result, f, indent=4)
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    except IOError as e:
        print(f"Error writing to config file: {e}")
        return False
    except KeyboardInterrupt:
        print("\nConfiguration cancelled.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    
    print(f"\nThis configuration was saved to {config_path.resolve()}")
    print(f"You can run the proxy with: 'python -m m365proxy -config {config_path.resolve()}'")
    print("Please review the file before launching the proxy.")
    print("")

    return True


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        config_path = Path(sys.argv[1]).resolve().tostr()
    else:
        config_path = Path.home().with_name("config.json").resolve().tostr()

    interactive_configure(config_path)
