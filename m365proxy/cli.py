"""Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import signal
import sys

from m365proxy.utils.shutdown import (
    graceful_shutdown,
    wait_for_shutdown_signal,
)

from m365proxy.workers import background_token_refresh, process_queue

from m365proxy.config import (
    IS_WINDOWS,
    get_app_data_dir,
    get_cmd_parser,
    load_config,
    setup_logging,
)
from m365proxy.controllers import start_smtp_server, stop_smtp_server


async def main() -> int:
    """Run the SMTP/POP3 proxy."""
    args = get_cmd_parser().parse_args()
    app_data_dir = get_app_data_dir(args.config)

    if args.command == "init-config":
        from m365proxy.helpers.configure import init_config
        return init_config(args.config or app_data_dir / "config.json")

    if args.command == "configure":
        from m365proxy.helpers.configure import interactive_configure
        return interactive_configure(
            args.config or app_data_dir / "config.json"
        )

    if args.command == "hash":
        from m365proxy.auth import hash_password
        print(hash_password(args.PASSWORD))
        return 0

    mode = "debug" if args.debug else "quiet" if args.quiet else None
    setup_logging(mode)

    config = load_config(args)

    if not config:
        logging.error("Failed to load configuration. Exiting.")
        return 1

    if args.command == "check-token":
        from m365proxy.auth import show_tokens
        return show_tokens()

    if args.command == "test":
        from m365proxy.core.smtp import send_test
        return await send_test()

    if args.command == "check-config":
        from pathlib import Path

        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(i) for i in obj]
            elif isinstance(obj, Path):
                return str(obj)
            return obj

        def sanitize_config(config):
            sanitized_config = config.copy()
            https_proxy = sanitized_config.get("https_proxy", {})
            if https_proxy:
                if "password" in https_proxy:
                    https_proxy["password"] = "****"
                sanitized_config["https_proxy"] = https_proxy
            return sanitized_config
        try:
            sanitized_config = sanitize_config(config)
            print(json.dumps(convert_paths(sanitized_config), indent=4))
        except Exception as e:
            print(f"Error converting config to JSON: {e}")
            return 1
        return 0

    if args.command == "check":
        from m365proxy.auth import get_access_token
        if await get_access_token():
            print("Access token is valid.")
        else:
            print("Access token is missing or invalid. "
                  "Run with 'login' to authenticate.",
                  file=sys.stderr)
            return 1
        return 0

    if args.command == "login":
        from m365proxy.auth import interactive_login
        return await interactive_login()

    shutdown_event = asyncio.Event()
    asyncio.create_task(background_token_refresh(shutdown_event))
    logging.info("Token refresh task started")

    asyncio.create_task(process_queue(shutdown_event))
    logging.info("Process mail queue task started")

    tls_context = None
    if config.get("tls"):
        import ssl
        tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        tls_context.load_cert_chain(
            certfile=config.get("tls")["tls_cert"],
            keyfile=config.get("tls")["tls_key"])
        logging.info("TLS context created.")

    smtp_controller = await start_smtp_server(config, tls_context)

    if isinstance(config.get("pop3_port"), int):
        from m365proxy.controllers.pop3 import start_pop3_server
        pop3_server = await start_pop3_server(config, tls_context)

    logging.info("Mail proxy is running. Press Ctrl+C or Enter to stop.")
    logging.info("Waiting for shutdown signal...")

    await wait_for_shutdown_signal(shutdown_event)

    await stop_smtp_server(smtp_controller)
    logging.info("SMTP Proxy stopped.")

    if 'pop3_server' in locals():
        from m365proxy.controllers.pop3 import stop_pop3_server
        await stop_pop3_server(pop3_server)

    await graceful_shutdown()
    logging.info("Mail proxy shutdown complete.")

    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, shutting down...")
        exit_code = 0
    except Exception:
        logging.exception("Unhandled exception in main loop")
        exit_code = 1

    raise SystemExit(exit_code)
