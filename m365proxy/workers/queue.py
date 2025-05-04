"""Process mail queue background task."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import logging
import json
from email import message_from_file
from email.message import EmailMessage
from email.policy import default
from pathlib import Path
from m365proxy.core.smtp import send_mail
from m365proxy.config import get_config_value


async def process_queue(shutdown_event: asyncio.Event, interval: int = 300):
    """Background task that processes the queued mail files."""
    logging.info("Mail queue processor started")
    queue_dir = Path(get_config_value("queue_dir"))

    while not shutdown_event.is_set():
        files = sorted(queue_dir.glob("*.meta.json"))
        for meta_file in files:
            try:
                base = meta_file.with_suffix("")
                eml_file = base.with_suffix(".eml")
                if not eml_file.exists():
                    logging.warning(f"Missing message file for {meta_file}")
                    meta_file.unlink()
                    continue

                # Read meta
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)

                # Read message
                with open(eml_file, encoding="utf-8") as f:
                    msg = message_from_file(f, policy=default)
                    if not isinstance(msg, EmailMessage):
                        msg = EmailMessage()

                # Try to resend
                try:
                    result = await send_mail(
                        meta["mail_from"], meta["rcpt_tos"], msg)
                    if not result:
                        logging.warning(
                            "Send returned False for "
                            f"{base.name}, will retry later")
                        continue
                except Exception as e:
                    logging.warning(
                        f"Exception during send for {base.name}: {e}")
                    continue

                # On success — delete both files
                eml_file.unlink()
                meta_file.unlink()
                logging.info(
                    f"Resent and deleted queued message {base.name}")

            except Exception as e:
                logging.warning(
                    f"Retry failed for {meta_file.name}: {e}")

        await asyncio.sleep(interval)
    logging.info("Mail queue processor stopped")
