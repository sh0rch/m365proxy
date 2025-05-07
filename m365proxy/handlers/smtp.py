"""SMTP handler."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import base64
import logging
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr

from aiosmtpd.smtp import AuthResult

from m365proxy.auth import check_credentials
from m365proxy.core.smtp import send_mail
from m365proxy.helpers.graph_helper import safe_graph_api_request
from m365proxy.core.mail_queue import save_to_queue

safe_send_mail = safe_graph_api_request(fallback=save_to_queue)(send_mail)


class SMTPHandler:
    """SMTP handler for processing incoming SMTP requests."""

    def __init__(self, mailboxes: list, allowed_domains: list = None) -> None:
        """Initialize the SMTP handler with mailboxes and allowed domains."""
        self.mailboxes = mailboxes
        self.allowed_from = {mbx["username"].lower() for mbx in mailboxes}
        self.allowed_domains = set(allowed_domains) \
            if allowed_domains else set()
        if '*' in self.allowed_domains:
            logging.warning(
                "Wildcard '*' in allowed domains, all domains are allowed.")
            logging.warning(
                "This is a security risk, please specify allowed domains "
                "or restrict access.")
        else:
            logging.info(f"Allowed domains: {self.allowed_domains}")

    async def auth_LOGIN(  # noqa: N802
            self,
            server,
            arg: list[str]
    ) -> AuthResult:
        """Handle LOGIN authentication mechanism."""
        if not arg:
            await server.push("501 5.5.4 No mechanism specified")
            return AuthResult(success=False, handled=True)

        mechanism = arg[0].upper()

        if mechanism != 'LOGIN':
            await server.push("504 5.7.4 Unrecognized authentication type")
            return AuthResult(success=False, handled=True)

        username_bytes = await server.challenge_auth(
            'VXNlcm5hbWU6',
            encode_to_b64=False,
            log_client_response=False)
        username = username_bytes.decode('utf-8', errors='replace')
        logging.debug("Username received: %s", username)
        password_bytes = await server.challenge_auth(
            'UGFzc3dvcmQ6',
            encode_to_b64=False,
            log_client_response=False)
        password = password_bytes.decode('utf-8', errors='replace')
        logging.debug("Password received: ******")
        if check_credentials(username, password):
            logging.info(f"Auth success: {username} from server")
            return AuthResult(success=True, handled=True)

        await server.push("535 5.7.8 Authentication credentials invalid")
        logging.error(f"Auth failed: {username} from server")
        return AuthResult(success=False, handled=True)

    async def auth_PLAIN(self, server, args):  # noqa: N802
        """Handle PLAIN authentication mechanism."""
        if len(args) < 2 or args[0] != "PLAIN":
            await server.push("501 5.5.4 No mechanism specified")
            return AuthResult(
                success=False,
                handled=True,
                message="Invalid PLAIN data"
            )

        parts = base64.b64decode(args[1]).decode(
            'utf-8', 'replace').split('\x00')
        if len(parts) != 3:
            await server.push("501 5.5.4 Invalid PLAIN data format")
            return AuthResult(success=False, handled=True,
                              message="Invalid PLAIN data format")

        [auth_id, username, password] = parts

        logging.debug(f"AUTH PLAIN: authzid=\"{auth_id}\", "
                      f"user={username}, password=******")

        if check_credentials(username, password):
            logging.info(f"Auth success: {username} from server")
            return AuthResult(success=True, handled=True)

        await server.push("535 5.7.8 Authentication credentials invalid")
        logging.error(f"Auth failed: {username} from server")
        return AuthResult(success=False, handled=True)

    async def handle_DATA(self, server, session, envelope):  # noqa: N802
        """Handle incoming DATA command."""
        try:
            smtp_from = envelope.mail_from.lower()
            _, parsed_smtp_from = parseaddr(smtp_from)
            # self.allowed_domains = set(allowed_domains)
            rcpt_domains = set([rcpt.split('@')[-1]
                               for rcpt in envelope.rcpt_tos])
            if '*' not in self.allowed_domains:
                denied = rcpt_domains - self.allowed_domains
                if denied:
                    logging.error(f"Denied recipient domain(s): {denied}")
                    return "550 Recipient domain not allowed"

            msg = BytesParser(policy=policy.default).parsebytes(
                envelope.original_content)
            _, parsed_header_from = parseaddr(msg.get("From", "").lower())

            if parsed_smtp_from != parsed_header_from:
                logging.error(
                    f"MAIL FROM ({parsed_smtp_from}) ≠ "
                    f"Header From ({parsed_header_from})"
                )
                return "550 MAIL FROM and From: header mismatch"

            if parsed_header_from not in self.allowed_from:
                logging.error(f"Sender not allowed: {parsed_header_from}")
                return "550 Sender not allowed"

            logging.info(f"Sending message from {parsed_smtp_from} to "
                         f"{envelope.rcpt_tos}")
            await safe_send_mail(parsed_smtp_from, envelope.rcpt_tos, msg)
            return "250 Message accepted for delivery"

        except Exception:
            logging.exception("Failed to send via Graph")
            return "451 Failed to send message"
