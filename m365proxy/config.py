"""Configuration management for m365proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import argparse
import json
import logging
import os
import platform
import sys
import textwrap
from logging.handlers import RotatingFileHandler
from pathlib import Path

from colorlog import ColoredFormatter
from dotenv import load_dotenv

from m365proxy import __description__, __version__
from m365proxy.utils import (
    detect_prog,
    get_app_data_dir,
    is_file_readable,
    is_file_writable,
    is_port_available,
    is_valid_email,
    parse_proxy_url,
    sanitize_url,
)

_config = {}
IS_WINDOWS = platform.system() == "Windows"

PROGRAMME = detect_prog()

log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')

usage = textwrap.dedent("""\
    %(prog)s version: %(version)s

    Usage:
        %(prog)s [options]
        %(prog)s [-config CONFIG] [command]

    Options:
        [-config CONFIG] [-token TOKEN] [-queue-dir QUEUE_DIR]
        [-log-file LOG_FILE] [-bind BIND_ADDRESS] [-smtp-port SMTP_PORT]
        [-pop3-port POP3_PORT] [-https-proxy HTTPS_PROXY] [-no-ssl]
        [-debug | -quiet] [ -h | --help ]

    Commands:
        [ init-config | configure | login | check-token | show-token |
          check-config | test | hash PASSWORD ]
    """) % {"prog": PROGRAMME, "version": __version__}


class CustomParser(argparse.ArgumentParser):
    """Custom argument parser for m365proxy."""

    def error(self, message):
        """Override error method to customize error handling."""
        print(usage, file=sys.stderr)
        # print(f"\nError: {message}\n\n", file=sys.stderr)
        self.exit(2, f"\nError: {message}\n\n")


def get_cmd_parser() -> CustomParser:
    """Create and return the command line argument parser."""
    app_data_dir = str(get_app_data_dir())
    parser = CustomParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=PROGRAMME,
        description=__description__,
        usage=usage,
        epilog=textwrap.dedent("""\
        Examples:
            %(prog)s
            %(prog)s init-config
            %(prog)s configure
            %(prog)s login
            %(prog)s -smtp-port 2525 -bind 0.0.0.0
            %(prog)s -config myconfig.json -token /tmp/mytoken.enc -quiet
            %(prog)s -config /tmp/myconfig.json -token /tmp/mytoken.enc"""
                               "-log-file /tmp/m365.log -log-level DEBUG")
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f" v{__version__} ",
        help=argparse.SUPPRESS
    )

    commands = parser.add_subparsers(
        title='Commands',
        dest="command",
        help="Start service (when no command is given)",
        metavar=""
    )
    commands.add_parser(
        "init-config", help="Create minimal default config.json")
    commands.add_parser(
        "configure",
        help="Interactive configuration"
    )
    commands.add_parser(
        "login",
        help="Run device login interactive flow"
    )
    commands.add_parser(
        "check-token",
        help="Check access token validity"
    )
    commands.add_parser(
        "show-token",
        help="Show token contents"
    )
    commands.add_parser(
        "check-config",
        help="Check existing configuration and show effective settings"
    )
    commands.add_parser("test", help="Send test email")
    hash_command = commands.add_parser(
        "hash",
        help="Hash password for use in config.json"
    )
    hash_command.add_argument(
        "PASSWORD",
        type=str,
        help="Password to hash"
    )

    parser.add_argument(
        "-config",
        type=str,
        help="Path to configuration file "
        f"(default: <{app_data_dir}>/config.json)"
    )
    parser.add_argument(
        "-queue-dir",
        type=str,
        help="Path to queue directory "
        f"(default: <{app_data_dir}>/queue)"
    )
    parser.add_argument(
        "-token",
        type=str,
        help="Path to token file "
        f"(default: <{app_data_dir}>/tokens.enc)"
    )
    parser.add_argument(
        "-log-file",
        type=str,
        help="Log file path "
        f"(default: <{app_data_dir}>/m365.log)"
    )
    parser.add_argument(
        "-log-level",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level for LOG_FILE (default: INFO)"
    )

    parser.add_argument(
        "-bind",
        type=str,
        default=None,
        help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "-smtp-port",
        type=int,
        default=None,
        help="SMTP listening port (default: 10025)"
    )
    parser.add_argument(
        "-pop3-port",
        type=int,
        default=None,
        help="POP3 listening port (default: None)"
    )
    parser.add_argument(
        "-https-proxy",
        type=str,
        help="HTTPS proxy server URL (e.g. proxy.local:3128)"
    )
    parser.add_argument(
        "-no-ssl",
        action="store_true",
        help="Disable SSL/TLS for SMTP and POP3"
    )

    parser_log = parser.add_mutually_exclusive_group()
    parser_log.add_argument(
        "-debug",
        action="store_true",
        help="Enable debug mode (CLI only)"
    )
    parser_log.add_argument(
        "-quiet",
        action="store_true",
        help="Suppress all output except errors (CLI only)"
    )

    return parser


def setup_logging(mode: str = None) -> None:
    """Set logging configuration."""
    logger = logging.getLogger()
    logger.handlers.clear()
    if mode == "debug":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if mode == "quiet":
        return

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.DEBUG)
    color_formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s] [%(levelname)s]%(reset)s %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'white',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red,bg_white',
        }
    )
    stderr_handler.setFormatter(color_formatter)
    logger.addHandler(stderr_handler)


def validate_mailboxes_config(mailboxes: list) -> bool:
    """Validate the mailboxes configuration."""
    mailboxes_usage = """\
\"mailboxes\" must be a list of
{
    "username": "email@domain.any",
    "password": "password_hash"
} """
    if not isinstance(mailboxes, list):
        raise ValueError(mailboxes_usage)

    for idx, mailbox in enumerate(mailboxes):
        if not isinstance(mailbox, dict):
            raise ValueError(f"mailboxes[{idx}] must be a dictionary. "
                             f"{mailboxes_usage}")
        username = mailbox.get("username")
        password = mailbox.get("password")
        if not username or not password:
            raise ValueError(f"mailboxes[{idx}] must contain both "
                             "'username' and 'password'")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError(f"mailboxes[{idx}] 'username' and 'password' "
                             "must be strings")
        if not is_valid_email(username):
            raise ValueError(f"mailboxes[{idx}]['username'] must be a valid "
                             "email address")
    return True


def load_config(args, path=None) -> dict:
    """Load configuration from file and environment variables."""
    global _config
    app_data_dir = str(get_app_data_dir())
    load_dotenv(dotenv_path=app_data_dir, override=True)

    config_path = args.config or os.getenv("M365_PROXY_CONFIG_FILE")
    try:
        if not config_path:
            config_path = f"{app_data_dir}/config.json"
    except IOError as e:
        logging.error(f"Error determining config path: {e}")
        return {}

    config_path = Path(path or config_path).resolve()
    config_dir = config_path.parent

    if not is_file_readable(config_path):
        logging.error(
            f"Config file '{config_path}' not found or not readable!")
        logging.error("Use 'init-config' or 'configure' to create a new one.")
        return {}

    with open(config_path) as f:
        try:
            _config = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from config file: {e}")
            return {}

    if not _config.get("logging") or not isinstance(_config["logging"], dict):
        _config["logging"] = {}

    log_cfg = _config["logging"]

    if args.log_file:
        log_cfg["log_file"] = args.log_file
    if args.log_level:
        log_cfg["log_level"] = args.log_level.upper()

    if "log_level" in log_cfg and "log_file" not in log_cfg:
        log_cfg["log_file"] = config_dir / "m365.log"

    if "log_file" in log_cfg and "log_level" not in log_cfg:
        log_cfg["log_level"] = "INFO"

    if "log_level" in log_cfg:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if log_cfg["log_level"] not in valid_levels:
            logging.warning(f"Invalid log level: {log_cfg['log_level']}"
                            ", defaulting to INFO.")
            log_cfg["log_level"] = "INFO"

    log_cfg["log_file"] = Path(log_cfg["log_file"]).resolve()
    log_cfg["log_level"] = log_cfg["log_level"].upper()
    if "log_file" in log_cfg and is_file_writable(log_cfg["log_file"]):
        file_handler = RotatingFileHandler(
            log_cfg["log_file"],
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(file_handler)
        logging.info("Logging to file: %s", log_cfg["log_file"])
    else:
        logging.error(
            f"Log file path '{log_cfg['log_file']}' is not writable.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        logging.error("Logging into the file will be disabled.")

    _config["logging"] = log_cfg

    token_path = args.token or os.getenv("M365_PROXY_TOKEN_FILE") or \
        _config.get("token_path") or \
        str(config_dir / "tokens.enc")
    if not token_path or not is_file_readable(Path(token_path)):
        logging.error(
            f"Token file '{token_path}' not found or not accessible!")
        logging.error("Use 'login' to create a new one.")
        return {}

    queue_dir = args.queue_dir or os.getenv("M365_PROXY_QUEUE_DIR") or \
        str(config_dir / "queue")
    try:
        Path(queue_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Error creating queue directory: {e}")
        return {}

    client_id = _config.get("client_id", "x")
    tenant_id = _config.get("tenant_id", "y")
    if client_id[0] == "x" or tenant_id[0] == "y":
        logging.error("Missing client_id or tenant_id in config file.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    mailboxes = _config.get("mailboxes")
    if not mailboxes or not isinstance(mailboxes, list):
        logging.error("Missing mailboxes in config file.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    try:
        validate_mailboxes_config(mailboxes)
    except ValueError as e:
        logging.error(f"Invalid mailboxes in config file: {e}")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    domains = _config.get("allowed_domains")
    if not domains or not isinstance(domains, list):
        logging.error("Missing allowed_domains in config file.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    if not all(isinstance(domain, str) for domain in domains):
        logging.error("allowed_domains must be a list of strings.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    if not _config.get("allowed_domains"):
        logging.error("Missing allowed_domains in config file.")
        logging.error(
            "Edit the config file or use 'configure' to create a new one.")
        return {}

    if "*" in domains:
        logging.warning("Allowed domains set to '*' - all domains are allowed."
                        " This is insecure!")
        logging.warning("Consider restricting to specific domains.")

    tls = None
    if not args.no_ssl:
        tls = _config.get("tls")
        if tls and isinstance(tls, dict):
            tls_cert = tls.get("tls_cert")
            tls_key = tls.get("tls_key")
            if not tls_cert or not isinstance(tls_cert, str) or \
                    not is_file_readable(Path(tls_cert)):
                logging.error(f"TLS certificate file '{tls_cert}' not found.")
                logging.error("Edit the config file or use 'configure' "
                              "to create a new one.")
                return {}
            else:
                _config["tls"]["tls_cert"] = Path(tls_cert).resolve()
            if not tls_key or not isinstance(tls_key, str) or \
                    not is_file_readable(Path(tls_key)):
                logging.error(f"TLS key file '{tls_key}' not found.")
                logging.error("Edit the config file or use 'configure' "
                              "to create a new one.")
                return {}
            else:
                _config["tls"]["tls_key"] = Path(tls_key).resolve()
            logging.info(
                "TLS will be enabled. Ensure you have the valid certificates."
            )
        else:
            logging.warning("TLS is not enabled. This is insecure!")
            logging.warning("Consider enabling TLS for secure connections.")

    bind_address = args.bind or _config.get("bind", "localhost")
    smtp_bind_port = args.smtp_port or _config.get("smtp_port", 10025)
    pop3_bind_port = args.pop3_port or _config.get("pop3_port", None)
    https_proxy = args.https_proxy or\
        os.getenv("https_proxy") or\
        os.getenv("http_proxy") or\
        os.getenv("HTTPS_PROXY") or\
        os.getenv("HTTP_PROXY") or\
        _config.get("https_proxy", {}).get("url")

    if https_proxy and isinstance(https_proxy, str):
        try:
            user = _config.get("https_proxy", {}).get("username", "")
            passwd = _config.get("https_proxy", {}).get("password", "")
            https_proxy = parse_proxy_url(https_proxy, user, passwd)
            if https_proxy == "":
                logging.error("Invalid HTTPS proxy URL.")
                return {}

            os.environ["HTTPS_PROXY"] = https_proxy
            os.environ["https_proxy"] = https_proxy
            sanitized_https_proxy = sanitize_url(https_proxy)
            logging.info("HTTPS proxy set to: %s", sanitized_https_proxy)

        except Exception as e:
            logging.error(f"Failed to encode proxy URL: {e}")
            return {}

    if not bind_address or not isinstance(bind_address, str):
        logging.error("Bind address must be a string.")
        logging.error("Edit the config file or use 'configure' "
                      "to create a new one.")
        return {}

    if not smtp_bind_port or not isinstance(smtp_bind_port, int):
        logging.error("SMTP bind port must be an integer.")
        logging.error("Edit the config file or use 'configure' "
                      "to create a new one.")
        return {}

    if pop3_bind_port and not isinstance(pop3_bind_port, int):
        logging.error("POP3 bind port must be an integer.")
        logging.error("Edit the config file or use 'configure' "
                      "to create a new one.")
        return {}

    if not is_port_available(bind_address, smtp_bind_port):
        logging.error(f"SMTP bind port {smtp_bind_port} is already in use "
                      f"on {bind_address}.")
        logging.error("Edit the config file or use '-smtp-port' "
                      "to try another one.")
        return {}

    if pop3_bind_port and not is_port_available(bind_address, pop3_bind_port):
        logging.error(f"POP3 bind port {pop3_bind_port} is already in use "
                      f"on {bind_address}.")
        logging.error("Edit the config file or use '-pop3-port' "
                      "to try another one.")
        return {}

    _config["token_path"] = token_path
    _config["https_proxy"] = https_proxy
    _config["bind"] = bind_address
    _config["smtp_port"] = smtp_bind_port
    _config["pop3_port"] = pop3_bind_port
    _config["queue_dir"] = str(queue_dir)

    return _config


def get_config() -> dict:
    """Return the current configuration."""
    return _config if _config else {}


def get_config_value(key: str, default=None) -> any:
    """Return the value of the specified configuration key."""
    if key in _config:
        return _config[key]
    else:
        return default


def set_config_value(key: str, value: any) -> None:
    """Set the value of the specified configuration key."""
    _config[key] = value


if __name__ == "__main__":
    print("Cannot run this script directly. Please use the main.py script.")
    sys.exit(1)
