"""POP3 handler."""
# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import logging
from base64 import b64decode
from m365proxy.auth import check_credentials
from m365proxy.core.pop3 import delete_message, get_message_raw, list_messages


class POP3Handler:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.authenticated = False
        self.username = None
        self.messages = []
        self.uids = []
        self.cache = {}
        self.deleted = set()
        self.awaiting_auth_plain = False
        self.awaiting_auth_login = False
        self.auth_login_stage = 0

    async def send(self, text: str | bytes) -> None:
        self.writer.write(text if isinstance(text, bytes) else text.encode())
        await self.writer.drain()

    async def handle(self):
        await self.send('+OK POP3 Proxy ready\r\n')

        while not self.writer.is_closing():
            try:
                line = await self.reader.readline()
                if not line:
                    break

                line = line.decode(errors='ignore').strip()
                if not line:
                    continue

                cmd, *args = line.split()
                cmd = cmd.upper()

                if self.awaiting_auth_plain:
                    try:
                        decoded = b64decode(line).decode()
                        parts = decoded.split('\x00')
                        username = parts[1] if len(parts) > 2 else parts[0]
                        password = parts[2] if len(parts) > 2 else parts[1]
                        self.awaiting_auth_plain = False

                        if check_credentials(username, password):
                            self.username = username
                            self.messages = await list_messages(self.username)
                            self.uids = [msg["id"] for msg in self.messages]
                            self.deleted.clear()
                            self.cache.clear()
                            self.authenticated = True
                            await self.send('+OK authenticated\r\n')
                        else:
                            await self.send('-ERR invalid credentials\r\n')
                            return
                    except Exception as e:
                        logging.error(f"AUTH PLAIN failed: {e}")
                        await self.send('-ERR AUTH PLAIN failed\r\n')
                    continue

                if self.awaiting_auth_login:
                    try:
                        decoded = b64decode(line).decode()
                        if self.auth_login_stage == 0:
                            self.username = decoded
                            self.auth_login_stage = 1
                            await self.send("+ UGFzc3dvcmQ6\r\n")
                        elif self.auth_login_stage == 1:
                            password = decoded
                            self.awaiting_auth_login = False
                            self.auth_login_stage = 0
                            if check_credentials(self.username, password):
                                self.messages = await list_messages(
                                    self.username)
                                self.uids = [
                                    msg["id"] for msg in self.messages]
                                self.deleted.clear()
                                self.cache.clear()
                                self.authenticated = True
                                await self.send('+OK authenticated\r\n')
                            else:
                                await self.send('-ERR invalid credentials\r\n')
                                return
                    except Exception as e:
                        logging.error(f"AUTH LOGIN failed: {e}")
                        await self.send('-ERR AUTH LOGIN failed\r\n')
                    continue

                logging.debug(f"POP3: {cmd} " \
                    f"{'*****' if cmd in ('PASS', 'PLAIN') else ' '.join(args)}")

                if cmd == "USER":
                    self.username = args[0] if args else None
                    await self.send('+OK user accepted\r\n')

                elif cmd == "PASS":
                    if not self.username or \
                            not args or \
                            not check_credentials(self.username, args[0]):
                        await self.send('-ERR invalid credentials\r\n')
                        return
                    try:
                        self.messages = await list_messages(self.username)
                        self.uids = [msg["id"] for msg in self.messages]
                        self.deleted.clear()
                        self.cache.clear()
                        self.authenticated = True
                        await self.send('+OK auth successful\r\n')
                    except Exception as e:
                        logging.error(f"Error retrieving messages: {e}")
                        await self.send('-ERR failed to list messages\r\n')

                elif cmd == "AUTH" and args:
                    method = args[0].upper()
                    if method == "PLAIN":
                        self.awaiting_auth_plain = True
                        await self.send('+ \r\n')
                    elif method == "LOGIN":
                        self.awaiting_auth_login = True
                        self.auth_login_stage = 0
                        await self.send("+ VXNlcm5hbWU6\r\n")
                    else:
                        await self.send('-ERR unsupported AUTH method\r\n')

                elif cmd == "STAT":
                    remaining = [
                        msg for i, msg in enumerate(self.messages)
                        if i not in self.deleted
                    ]
                    await self.send(f"+OK {len(remaining)} "
                                f"{sum(msg['size'] for msg in remaining)}\r\n")

                elif cmd == "LIST":
                    await self.send(f"+OK {len(self.messages)} messages:\r\n")
                    for i, msg in enumerate(self.messages):
                        if i not in self.deleted:
                            await self.send(f"{i+1} {msg['size']}\r\n")
                    await self.send('.\r\n')

                elif cmd == "UIDL":
                    if args:
                        idx = int(args[0]) - 1
                        if 0 <= idx < len(self.uids) and \
                                idx not in self.deleted:
                            await self.send(
                                f"+OK {idx+1} {self.uids[idx]}\r\n")
                        else:
                            await self.send(
                                '-ERR no such message\r\n')
                    else:
                        await self.send(
                            f"+OK {len(self.uids)} messages:\r\n")
                        for i, uid in enumerate(self.uids):
                            if i not in self.deleted:
                                await self.send(f"{i+1} {uid}\r\n")
                        await self.send('.\r\n')

                elif cmd == "RETR":
                    idx = int(args[0]) - 1
                    if idx < 0 or \
                            idx >= len(self.messages) or idx in self.deleted:
                        await self.send('-ERR no such message\r\n')
                        continue
                    try:
                        msg_id = self.messages[idx]["id"]
                        if msg_id in self.cache:
                            raw = self.cache[msg_id]
                        else:
                            raw = await get_message_raw(self.username, msg_id)
                            self.cache[msg_id] = raw
                        await self.send('+OK message follows\r\n')
                        await self.send(raw)
                        await self.send('\r\n.\r\n')
                    except Exception as e:
                        logging.error(f"Error retrieving message: {e}")
                        await self.send('-ERR failed to retrieve message\r\n')

                elif cmd == "DELE":
                    idx = int(args[0]) - 1
                    if 0 <= idx < len(self.messages):
                        self.deleted.add(idx)
                        await self.send('+OK marked for deletion\r\n')
                    else:
                        await self.send('-ERR no such message\r\n')

                elif cmd == "RSET":
                    self.deleted.clear()
                    await self.send('+OK\r\n')

                elif cmd == "NOOP":
                    await self.send('+OK\r\n')

                elif cmd == "QUIT":
                    if self.deleted:
                        await self.send('+OK Deleting marked messages\r\n')
                        for idx in self.deleted:
                            try:
                                msg_id = self.messages[idx]["id"]
                                etag = self.messages[idx].get("etag")
                                await delete_message(
                                    self.username, msg_id, etag)
                            except Exception as e:
                                logging.error(
                                    f"Error deleting message {msg_id}: {e}")
                                await self.send(
                                    '-ERR failed to delete message\r\n')
                    await self.send('+OK Bye\r\n')
                    break

                else:
                    await self.send('-ERR unknown command\r\n')

            except Exception as e:
                logging.exception("POP3 command error")
                await self.send('-ERR internal server error\r\n')

        self.writer.close()
        await self.writer.wait_closed()
