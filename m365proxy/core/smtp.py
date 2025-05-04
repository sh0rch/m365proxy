"""m365proxy.service.smtp - SMTP functions."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import base64
import logging
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr

from m365proxy.config import get_config_value
from m365proxy.core.graph_api import api_request


def format_recipients(addresses: list[str]) -> list[dict]:
    """Format email addresses for Microsoft Graph API."""
    return [{"emailAddress": {"address": addr.strip()}} for addr in addresses]


def split_recipients(
        msg: EmailMessage,
        rcpt_tos: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split recipients into To, Cc, and Bcc lists."""
    to_c = len(getaddresses(msg.get_all("To", [])))
    cc_c = len(getaddresses(msg.get_all("Cc", [])))
    bcc_c = len(getaddresses(msg.get_all("Bcc", [])))

    total = to_c + cc_c + bcc_c
    if total != len(rcpt_tos):
        logging.warning("Header count does not match RCPT TO count. "
                        "Will fallback to treating all as 'To'.")
        return rcpt_tos, [], []

    to = rcpt_tos[0:to_c] or []
    cc = rcpt_tos[to_c:to_c + cc_c] or []
    bcc = rcpt_tos[to_c + cc_c:] or []

    return to, cc, bcc


async def send_mail(
        mail_from: str,
        rcpt_tos: list[str], msg: EmailMessage) -> bool:
    """Send an email using Microsoft Graph API."""
    _, from_address = parseaddr(msg.get("From"))

    if from_address != mail_from:
        logging.error(f"SMTP MAIL FROM[{mail_from}] is not "
                      "equal to From[{from_address}] address")
        return False

    html_body = None
    text_body = None
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = part.get_content_disposition()
            content_id = part.get("Content-ID")

            if disposition == "attachment" or \
                    (disposition is None and content_id):
                content = part.get_payload(decode=True)
                filename = part.get_filename() or content_id or "attachment"

                attachment_entry = {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": filename,
                    "contentBytes": base64.b64encode(content).decode("utf-8")
                }

                if content_id:
                    cid_clean = content_id.strip("<>")
                    attachment_entry["isInline"] = True
                    attachment_entry["contentId"] = cid_clean

                attachments.append(attachment_entry)

            elif ctype == "text/html":
                html_body = part.get_payload(decode=True).decode(
                    part.get_content_charset("utf-8"), errors="replace")
            elif ctype == "text/plain" and not text_body:
                text_body = part.get_payload(decode=True).decode(
                    part.get_content_charset("utf-8"), errors="replace")
    else:
        ctype = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        body_text = payload.decode(
            msg.get_content_charset("utf-8"), errors="replace")
        if ctype == "text/html":
            html_body = body_text
        else:
            text_body = body_text

    content_type = "HTML" if html_body else "Text"
    body_content = html_body if html_body else text_body or ""

    to, cc, bcc = split_recipients(msg, rcpt_tos)
    logging.debug(f"Recipients: To: {to}, Cc: {cc}, Bcc: {bcc}")

    graph_message = {
        "message": {
            "subject": msg.get("Subject", ""),
            "body": {
                "contentType": content_type,
                "content": body_content
            },
            "toRecipients": format_recipients(to),
            "ccRecipients": format_recipients(cc),
            "bccRecipients": format_recipients(bcc),
        }
    }

    if attachments:
        total_size = sum(len(
            base64.b64decode(a["contentBytes"])) for a in attachments)
        limit_mb = get_config_value("attachment_limit_mb", 80)
        if total_size > limit_mb * 1024 * 1024:
            raise Exception("Email exceeds attachment size limit: "
                            f"{total_size / 1024 / 1024:.2f} MB")
        graph_message["message"]["attachments"] = attachments

    r = await api_request("POST",
                          f"/users/{from_address}/sendMail",
                          json=graph_message)

    if r is None:
        logging.error("Graph send returned None (possible network failure)")
        return False

    if r.status_code in (200, 202):
        logging.info(f"Email sent as {from_address} via Graph API")
        return True
    else:
        logging.error(f"Graph send failed ({r.status_code}): {r.text}")
        return False


async def send_test() -> None:
    """Send a test email to the configured mailbox."""
    msg = EmailMessage()
    sender = get_config_value("user")
    recipient = get_config_value("user")
    mailbox = get_config_value("mailboxes")[0]["username"]

    msg["From"] = mailbox
    msg["Sender"] = sender
    msg["To"] = recipient
    msg["Subject"] = "SMTP Proxy Test"
    msg.set_content("This is a test message from SMTP Proxy.")

    if await send_mail(mailbox, [recipient], msg):
        print("✅ Test message sent")
    else:
        print("❌ Test message failed")
