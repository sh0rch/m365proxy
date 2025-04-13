# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import logging
import base64
from email.message import EmailMessage
from email.utils import parseaddr, getaddresses

from m365proxy.config import get_config_value
from m365proxy.graph_api import api_request

def format_recipients(addresses):
    return [{"emailAddress": {"address": addr.strip()}} for addr in addresses]

def split_recipients(msg, rcpt_tos):
    to_c = len(getaddresses(msg.get_all("To", [])))
    cc_c = len(getaddresses(msg.get_all("Cc", [])))
    bcc_c = len(getaddresses(msg.get_all("Bcc", [])))

    #to_c = len(rcpt_tos) if to_c == 0 else to_c
    total = to_c + cc_c + bcc_c

    if total != len(rcpt_tos):
        logging.warning("Header count does not match RCPT TO count. Will fallback to treating all as 'To'.")
        return rcpt_tos, [], []
    
    to = rcpt_tos[0:to_c] or []
    cc = rcpt_tos[to_c:to_c + cc_c] or []
    bc = rcpt_tos[to_c + cc_c:] or []

    return to, cc, bc

async def send_mail(mail_from, rcpt_tos, msg):
    _, from_address = parseaddr(msg.get("From"))

    if from_address != mail_from:
        logging.error(f"SMTP MAIL FROM[{mail_from}] is not equal to From[{from_address}] address")
        return
    
    html_body = None
    text_body = None
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = part.get_content_disposition()
            content_id = part.get("Content-ID")

            if disposition == "attachment" or (disposition is None and content_id):
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
                html_body = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'), errors="replace")
            elif ctype == "text/plain" and not text_body:
                text_body = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'), errors="replace")
    else:
        ctype = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        body_text = payload.decode(msg.get_content_charset('utf-8'), errors="replace")
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
        total_size = sum(len(base64.b64decode(a["contentBytes"])) for a in attachments)
        if total_size > get_config_value("attachment_limit_mb", 80) * 1024 * 1024:
            raise Exception(f"❗ Email exceeds attachment size limit: {total_size / 1024 / 1024:.2f} MB")
        graph_message["message"]["attachments"] = attachments

    r = await api_request("POST", f"/users/{from_address}/sendMail", json=graph_message,)

    if r.status_code in (200, 202):
        logging.info(f"Email sent as {from_address} via Graph API")
    else:
        logging.error(f"Graph send failed ({r.status_code}): {r.text}")
        return False

async def send_test():
    msg = EmailMessage()
    msg["From"] = get_config_value("mailboxes")[0]["username"]
    msg["Sender"] = get_config_value("user")
    msg["To"] = get_config_value("user")
    msg["Subject"] = "SMTP Proxy Test"
    msg.set_content("This is a test message from SMTP Proxy.")
    print(msg)
    if await send_mail(msg["From"], [msg["To"]], msg):
        print("Test message sent")

async def get_message_raw(mailbox: str, message_id: str) -> bytes:
    r = await api_request('GET', f"/users/{mailbox}/messages/{message_id}/$value")
    return r.content

async def delete_message(mailbox: str, message_id: str, etag: str) -> bool:
    url = f"/users/{mailbox}/messages/{message_id}"
    headers = {}
    headers["If-Match"] = etag
    r = await api_request('DELETE', url, headers=headers)
    if r.status_code == 204:
        logging.info(f"Deleted message {message_id} for {mailbox}")
        return True
    elif r.status_code == 412:
        logging.warning(f"Message {message_id} was modified and not deleted")
        return False
    else:
        logging.error(f"Unexpected response {r.status_code} for deleting {message_id}")
        return False

async def list_messages(username: str) -> list[dict]:
    messages = []
    url = f"/users/{username}/mailFolders/Inbox/messages?$top=50"

    while url:
        r = await api_request("GET", url)
        result = r.json()
        
        for msg in result.get("value", []):
            msg_id = msg.get("id")
            if not msg_id:
                continue
            logging.debug(f"Processing message ID: {msg_id}")
            detail_url = f"/users/{username}/messages/{msg_id}"
            detail_r = await api_request("GET", detail_url)

            raw = detail_r.content
            size = len(raw)
            etag = msg.get("@odata.etag")
            attachments = []
            if msg.get("hasAttachments"):
                logging.debug(f"Message {msg_id} has attachments, processing...")
                attachments_url = f"/users/{username}/messages/{msg_id}/attachments?$select=id,size"
                attachments_r = await api_request("GET", attachments_url)
                
                for att in attachments_r.json().get("value", []):
                    att_id = att.get("id")
                    if att_id:
                        logging.debug(f"Attachment ID: {att_id}, Size: {att.get('size')}")
                        size += att.get("size")
                        attachments.append({
                            "id": att_id,
                            "size": att.get("size")
                        })

            logging.debug(f"Message ID: {msg_id}, Size: {size}, ETag: {etag}")
            messages.append({
                "id": msg_id,
                "size": size,
                "etag": etag,
                "attachments": attachments
            })

        url = result.get('@odata.nextLink')

    return messages