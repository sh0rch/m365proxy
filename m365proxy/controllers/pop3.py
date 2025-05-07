"""Start and stop controller for POP3 protocol."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import ssl
import logging
import asyncio
from m365proxy.handlers import POP3Handler, POP3StartTLSHandler


class POP3Server:
    """POP3 server class to handle POP3 connections."""

    def __init__(self,
                 config: dict, ssl_context: ssl.SSLContext = None) -> None:
        """Initialize the POP3 server with configuration."""
        self.config = config
        self.ssl_context = ssl_context
        self.bind = config.get("bind", "")
        self.sport = config.get("pop3s_port", None)
        self.port = config.get("pop3_port", None)
        self.starttls = config.get("starttls", False)
        self.server = None

    async def start(self) -> None:
        """Start the POP3 server."""
        server_type = "POP3S" if self.sport else "POP3"
        try:
            if self.port is None and self.sport is None:
                logging.error("No valid port configured for POP3 server.")
                return
            logging.info(f"Starting {server_type} server on "
                         f"{self.bind}:{self.port or self.sport}")
            self.server = await asyncio.start_server(
                self.handle_client,
                self.bind,
                self.port or self.sport,
                ssl=self.ssl_context if self.sport else None
            )

            if self.ssl_context:
                stype = "SSL/TLS" if self.sport else "STARTTLS"
                logging.info(
                    f"{stype} enabled for {server_type}")

            addr = self.server.sockets[0].getsockname()
            logging.info(f"{server_type} server started on {addr}")

        except Exception as e:
            logging.error(f"Failed to start {server_type} server: {e}")

    async def handle_client(self, reader, writer) -> None:
        """Handle a client connection."""
        if self.port and self.starttls:
            handler = POP3StartTLSHandler(reader, writer, self.ssl_context)
        else:
            handler = POP3Handler(reader, writer)
        await handler.handle()

    async def stop(self) -> None:
        """Stop the POP3 server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            server_type = "POP3S" if self.sport else "POP3"
            logging.info(f"{server_type} server "
                         f"on {self.sport or self.port} stopped")


async def start_pop3_server(
        config: dict,
        ssl_context: ssl.SSLContext = None) -> list[POP3Server]:
    """Initialize and start the POP3 server(s)."""
    servers = []
    bind_addr = config.get("bind", "")
    enable_starttls = bool(config.get("tls") and config.get("pop3_port"))
    if bool(config.get("pop3_port")):
        pop3_config = {
            "bind": bind_addr,
            "pop3_port": config.get("pop3_port"),
            "starttls": enable_starttls
        }
        srv = POP3Server(pop3_config, ssl_context=ssl_context)
        await srv.start()
        servers.append(srv)

    if bool(config.get("pop3s_port")):
        pop3s_config = {
            "bind": bind_addr,
            "pop3s_port": config.get("pop3s_port")
        }
        srvs = POP3Server(pop3s_config, ssl_context=ssl_context)
        await srvs.start()
        servers.append(srvs)

    return servers


async def stop_pop3_server(servers: list[POP3Server]) -> None:
    """Stop the given POP3 server instance."""
    for srv in servers:
        await srv.stop()
