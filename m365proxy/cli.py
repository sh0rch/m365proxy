# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import sys
import signal
import json
from aiosmtpd.controller import Controller
import logging
from m365proxy.config import IS_WINDOWS, get_app_data_dir, get_cmd_parser, load_config, setup_logging
from m365proxy.proxies import SMTPHandler

def trigger_shutdown(shutdown_event: asyncio.Event) -> None:
        if not shutdown_event.is_set():
            logging.info("Shutdown signal received. Stopping...")
            shutdown_event.set()

async def wait_for_shutdown_signal(shutdown_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def keyboard_interrupt():
        try:
            input()
        except EOFError:
            pass
        trigger_shutdown(shutdown_event)

    if IS_WINDOWS:
        loop.run_in_executor(None, keyboard_interrupt)
        try:
            signal.signal(signal.SIGINT, lambda s, f: trigger_shutdown(shutdown_event))
        except Exception as e:
            logging.warning(f"Signal handling not fully supported: {e}")
    else:
        try:
            loop.add_signal_handler(signal.SIGINT, lambda: trigger_shutdown(shutdown_event))
            loop.add_signal_handler(signal.SIGTERM, lambda: trigger_shutdown(shutdown_event))
        except NotImplementedError:
            logging.warning("Signal handlers not supported, fallback to input()")
            loop.run_in_executor(None, keyboard_interrupt)

    await shutdown_event.wait()

async def graceful_shutdown():
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if not tasks:
        return

    logging.info("Cancelling %d running task(s)...", len(tasks))

    for task in tasks:
        task.cancel()

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logging.warning(f"Exception during shutdown: {e}")

    logging.info("Shutdown complete.")

async def background_token_refresh(shutdown_event: asyncio.Event) -> None:
    from m365proxy.auth import refresh_token_if_needed
    try:
        while not shutdown_event.is_set():
            if not await refresh_token_if_needed():
                logging.error("Token refresh failed. Triggering shutdown.")
                trigger_shutdown(shutdown_event)
                break
            else:
                logging.info("Token refreshed. Sleeping for 3 days.")
                await asyncio.sleep(3 * 24 * 60 * 60)

    except asyncio.CancelledError:
        logging.info("Background token refresh cancelled.")
        raise

async def main() -> int:

    args = get_cmd_parser().parse_args()
    app_data_dir = get_app_data_dir(args.config)

    if args.command == "init-config":
        from m365proxy.configure import init_config
        return init_config(args.config or app_data_dir / "config.json")
    
    if args.command == "configure":
        from m365proxy.configure import interactive_configure
        return interactive_configure(args.config or app_data_dir / "config.json")
    
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
        from m365proxy.mail import send_test
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
        try:
            print(json.dumps(convert_paths(config), indent=4))
        except Exception as e:
            print(f"Error converting config to JSON: {e}")
            return 1
        return 0

    if args.command == "check":
        from m365proxy.auth import get_access_token
        if await get_access_token():
            print("Access token is valid.")
        else:
            print("Access token is missing or invalid. Run with 'login' to authenticate.", file=sys.stderr)
            return 1
        return 0

    if args.command == "login":
        from m365proxy.auth import interactive_login
        return await interactive_login()
    
    shutdown_event = asyncio.Event()
    asyncio.create_task(background_token_refresh(shutdown_event))
    logging.info("Token refresh task started")
    
    logging.info("Starting mail proxy...")
    smtp_handler = SMTPHandler(config.get("mailboxes"), config.get("allowed_domains"))
    
    tls_context = None
    if config.get("tls"):
        if "ssl" not in sys.modules:
            import ssl
        tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        tls_context.load_cert_chain(
            certfile=config["tls"]["tls_cert"], 
            keyfile=config["tls"]["tls_key"])
        smtp_controller = Controller(smtp_handler,
                                    hostname=config["bind"],
                                    port=config["smtp_port"],
                                    require_starttls=True,
                                    tls_context=tls_context)
        logging.info(f"TLS enabled with cert: {config['tls']['tls_cert']}, key: {config['tls']['tls_key']}")
    else:
        smtp_controller = Controller(smtp_handler,
                                    hostname=config["bind"],
                                    port=config["smtp_port"],
                                    auth_require_tls=False)
   
    smtp_controller.start()
    logging.info(f"SMTP Proxy started on {config['bind']}:{config['smtp_port']}")

    if isinstance(config.get("pop3_port"), int):
        from m365proxy.proxies import start_pop3
        if config.get("tls"):
            if tls_context is None:
                logging.error("TLS context not initialized")
                return 1
            pop3_controller = start_pop3(host=config["bind"], port=config["pop3_port"], tls_context=tls_context)
            logging.info(f"TLS enabled for POP3 with cert: {config['tls']['tls_cert']}, key: {config['tls']['tls_key']}")
        else:
            pop3_controller = start_pop3(host=config["bind"], port=config["pop3_port"])
        logging.info(f"POP3 Proxy started on {config['bind']}:{config['pop3_port']}")

    logging.info("Mail proxy is running. Press Ctrl+C or Enter to stop.")
    logging.info("Waiting for shutdown signal...")

    await wait_for_shutdown_signal(shutdown_event)
   
    smtp_controller.stop()
    logging.info("SMTP Proxy stopped.")

    if 'pop3_controller' in locals():
        from m365proxy.proxies import stop_pop3
        stop_pop3(pop3_controller) 
        logging.info("POP3 Proxy stopped.")

    #if 'pop3_controller' in locals() and callable(getattr(pop3_controller, "shutdown", None)):
    #    await pop3_controller.shutdown()

    await graceful_shutdown()
    logging.info("Mail proxy shutdown complete.")

    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, shutting down...")
        exit_code = 0
    except Exception as e:
        logging.exception("Unhandled exception in main loop")
        exit_code = 1

    raise SystemExit(exit_code)
