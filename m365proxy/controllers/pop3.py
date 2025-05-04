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
from m365proxy.handlers import POP3Handler


class POP3Server:
    def __init__(self,
                 config: dict, ssl_context: ssl.SSLContext = None) -> None:
        self.config = config
        self.ssl_context = ssl_context
        self.bind = config.get("bind", "localhost")
        self.port = config.get("pop3_port", 10110)
        self.server = None

    async def start(self) -> None:
        """Start the POP3 server."""
        try:
            self.server = await asyncio.start_server(
                self.handle_client,
                self.bind,
                self.port,
                ssl=self.ssl_context if self.config.get("tls") else None
            )

            if self.ssl_context:
                logging.info("TLS enabled for POP3 with cert: "
                             f"{self.config['tls']['tls_cert']}, "
                             f"key: {self.config['tls']['tls_key']}")

            addr = self.server.sockets[0].getsockname()
            logging.info(f"POP3 server started on {addr}")

        except Exception as e:
            logging.error(f"Failed to start POP3 server: {e}")

    async def handle_client(self, reader, writer) -> None:
        """Handle a client connection."""
        handler = POP3Handler(reader, writer)
        await handler.handle()

    async def stop(self) -> None:
        """Stop the POP3 server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logging.info("POP3 server stopped")


async def start_pop3_server(config: dict,
                            ssl_context: ssl.SSLContext = None) -> POP3Server:
    """Initialize and start the POP3 server."""
    server = POP3Server(config, ssl_context)
    await server.start()
    return server


async def stop_pop3_server(server: POP3Server) -> None:
    """Stop the given POP3 server instance."""
    await server.stop()
