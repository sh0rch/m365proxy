"""Start and stop controller for SMTP protocol."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import logging
from ssl import SSLContext

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP
from m365proxy.handlers import SMTPHandler


class SMTPServer:
    def __init__(self, config: dict, tls_context: SSLContext = None):
        self.config = config
        self.tls_context = tls_context
        self.controller = None

    async def start(self):
        mailboxes = self.config.get("mailboxes")
        domains = self.config.get("allowed_domains")
        bind = self.config.get("bind", "127.0.0.1")
        smtp_port = self.config.get("smtp_port", 10025)

        handler = SMTPHandler(mailboxes, domains)

        self.controller = Controller(
            handler,
            hostname=bind,
            port=smtp_port,
            tls_context=self.tls_context if self.config.get("tls") else None,
            require_starttls=bool(self.config.get("tls")),
            auth_require_tls=False,
            ready_timeout=10.0
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.controller.start)

        logging.info(
            f"SMTP Proxy started on {bind}:{smtp_port} "
            f"{'(TLS)' if self.tls_context else '(plain)'}"
        )

    async def stop(self):
        if self.controller:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.controller.stop)
            logging.info("SMTP Proxy stopped")


async def start_smtp_server(
        config: dict, tls_context: SSLContext = None) -> SMTPServer:
    """Async wrapper to start SMTP server."""
    server = SMTPServer(config, tls_context)
    await server.start()
    return server


async def stop_smtp_server(server: SMTPServer):
    """Stop the SMTP server."""
    await server.stop()
