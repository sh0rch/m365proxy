"""Mail queue processing for SMTP/POP3 proxy."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import json
import logging
from pathlib import Path
from email.message import EmailMessage
from email.policy import default
from m365proxy.config import get_config_value
from functools import wraps
from requests.exceptions import ConnectionError, Timeout, HTTPError


def save_to_queue(mail_from: str, rcpt_tos: list[str], msg: EmailMessage):
    """Save the email message to the queue directory."""
    queue_dir = Path(get_config_value("queue_dir"))
    idx = len(list(queue_dir.glob("*.meta.json")))
    base = queue_dir / f"mail_{idx:04d}"
    with open(base.with_suffix(".eml"), "w", encoding="utf-8") as f:
        f.write(msg.as_string(policy=default))
    with open(base.with_suffix(".meta.json"), "w", encoding="utf-8") as f:
        json.dump({"mail_from": mail_from, "rcpt_tos": rcpt_tos}, f)
    logging.warning(f"Queued message due to error: {base.name}")
