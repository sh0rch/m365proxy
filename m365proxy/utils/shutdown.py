"""Shutdown signal handling for m365proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import sys
import asyncio
import logging
import signal
from m365proxy.config import IS_WINDOWS


def trigger_shutdown(shutdown_event: asyncio.Event) -> None:
    """Trigger a shutdown event."""
    if not shutdown_event.is_set():
        logging.info("Shutdown signal received. Stopping...")
        shutdown_event.set()


async def wait_for_shutdown_signal(shutdown_event: asyncio.Event) -> None:
    """Wait for a shutdown signal (Ctrl+C or Enter)."""
    loop = asyncio.get_running_loop()

    def keyboard_interrupt():
        try:
            if sys.stdin is None or not sys.stdin.isatty():
                logging.warning("stdin not available, skipping input() wait.")
                return
            input()
        except EOFError:
            pass
        except RuntimeError:
            pass
        trigger_shutdown(shutdown_event)

    if IS_WINDOWS:
        loop.run_in_executor(None, keyboard_interrupt)
        try:
            signal.signal(signal.SIGINT, lambda s,
                          f: trigger_shutdown(shutdown_event))
        except Exception as e:
            logging.warning(f"Signal handling not fully supported: {e}")
    else:
        try:
            loop.add_signal_handler(signal.SIGINT,
                                    lambda: trigger_shutdown(shutdown_event))
            loop.add_signal_handler(signal.SIGTERM,
                                    lambda: trigger_shutdown(shutdown_event))
        except NotImplementedError:
            logging.warning(
                "Signal handlers not supported, fallback to input()")
            loop.run_in_executor(None, keyboard_interrupt)

    await shutdown_event.wait()


async def graceful_shutdown():
    """Gracefully shutdown all running tasks."""
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
