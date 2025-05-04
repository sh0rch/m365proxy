"""m365proxy.service.pop3 - POP3 functions."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import logging

from m365proxy.core.graph_api import api_request
from m365proxy.helpers.graph_helper import safe_graph_api_request


@safe_graph_api_request(fallback=None)
async def get_message_raw(mailbox: str, message_id: str) -> bytes:
    """Get the raw content of a message."""
    r = await api_request(
        "GET",
        f"/users/{mailbox}/messages/{message_id}/$value"
    )
    return r.content


@safe_graph_api_request(fallback=None)
async def delete_message(mailbox: str, message_id: str, etag: str) -> bool:
    """Delete a message using its ID and ETag."""
    url = f"/users/{mailbox}/messages/{message_id}"
    headers = {"If-Match": etag}
    r = await api_request("DELETE", url, headers=headers)

    if r.status_code == 204:
        logging.info(f"Deleted message {message_id} for {mailbox}")
        return True
    elif r.status_code == 412:
        logging.warning(f"Message {message_id} was modified and not deleted")
        return False
    else:
        logging.error(
            f"Unexpected response {r.status_code} for deleting {message_id}")
        return False


@safe_graph_api_request(fallback=[])
async def list_messages(username: str) -> list[dict]:
    """List messages in the mailbox."""
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

            # Get message details
            detail_url = f"/users/{username}/messages/{msg_id}"
            detail_r = await api_request("GET", detail_url)
            raw = detail_r.content
            size = len(raw)

            etag = msg.get("@odata.etag")
            attachments = []

            if msg.get("hasAttachments"):
                logging.debug(
                    f"Message {msg_id} has attachments, processing...")
                attachments_url = f"/users/{username}/messages/{msg_id}" \
                    "/attachments?$select=id,size"
                attachments_r = await api_request("GET", attachments_url)

                for att in attachments_r.json().get("value", []):
                    att_id = att.get("id")
                    if att_id:
                        logging.debug(f"Attachment ID: {att_id},"
                                      " Size: {att.get('size')}")
                        size += att.get("size", 0)
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

        url = result.get("@odata.nextLink")

    return messages
