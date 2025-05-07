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
from m365proxy.handlers.smtp import SMTPHandler


class SMTPServer:
    """SMTP server class to handle SMTP connections."""

    def __init__(self, config: dict, tls_context: SSLContext = None):
        """Initialize the SMTP server with configuration."""
        self.tls_context = tls_context
        self.server = None
        self.sport = config.get("smtps_port", None)
        self.port = config.get("smtp_port", None)
        self.bind = config.get("bind", "localhost")
        self.mailboxes = config.get("mailboxes")
        self.domains = config.get("allowed_domains")
        self.type = None

    async def start(self):
        """Start the SMTP server."""
        handler = SMTPHandler(self.mailboxes, self.domains)
        port = self.port or self.sport

        if self.sport and self.tls_context:
            mode = "(SSL/TLS mode)"
            self.type = "SMTPS"
        elif self.port and self.tls_context:
            mode = "(STARTTLS mode)"
            self.type = "SMTP"
        else:
            mode = "(plain mode)"
            self.type = "SMTP"
        logging.info(
            f"Starting {self.type} server on {self.bind}:{port} {mode}")
        if self.type == "SMTP":

            self.server = Controller(
                handler,
                hostname=self.bind,
                port=port,
                tls_context=self.tls_context,
                auth_require_tls=bool(self.tls_context and self.sport),
                require_starttls=bool(self.tls_context and self.port),
                ready_timeout=10.0
            )

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.server.start)
        else:
            loop = asyncio.get_running_loop()
            self.server = await loop.create_server(
                lambda: SMTP(
                    handler,
                    require_starttls=False,
                    auth_require_tls=True
                ),
                host=self.bind,
                port=port,
                ssl=self.tls_context
            )

        logging.info(
            f"{self.type} server started on {self.bind}:{port} {mode}")

    async def stop(self):
        """Stop the SMTP server."""
        if self.server:
            if self.type == "SMTP":
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.server.stop)
            else:
                self.server.close()
                await self.server.wait_closed()
            logging.info(f"{self.type} server stopped")


async def start_smtp_server(
    config: dict, tls_context: SSLContext = None
) -> list:
    """Start one or three SMTP servers: STARTTLS and/or SMTP(S)."""
    servers = []
    smtp_config = {
        "smtp_port": config.get("smtp_port"),
        "smtps_port": config.get("smtps_port"),
        "bind": config.get("bind", "localhost"),
        "mailboxes": config.get("mailboxes"),
        "allowed_domains": config.get("allowed_domains"),
    }

    if config.get("smtp_port"):
        smtp_config["smtps_port"] = None
        smtp_server = SMTPServer(smtp_config, tls_context)
        await smtp_server.start()
        servers.append(smtp_server)

    if config.get("smtps_port") and tls_context:
        smtp_config["smtp_port"] = None
        smtp_config["smtps_port"] = config.get("smtps_port")
        smtps_server = SMTPServer(smtp_config, tls_context)
        await smtps_server.start()
        servers.append(smtps_server)

    return servers


async def stop_smtp_server(servers: list):
    """Stop the SMTP server."""
    for server in servers:
        await server.stop()
