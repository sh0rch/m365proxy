# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import socketserver
from m365proxy.mail import send_mail, list_messages, get_message_raw, delete_message
from m365proxy.auth import check_credentials
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from aiosmtpd.smtp import AuthResult
import logging
import asyncio
import base64
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def start_pop3(host: str, port: int) -> ThreadedTCPServer:
    server = ThreadedTCPServer((host, port), POP3Handler)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, server.serve_forever)
    return server

def stop_pop3(server: ThreadedTCPServer):
    server.shutdown()
    server.server_close()
class SMTPHandler:
    def __init__(self, mailboxes: list, allowed_domains: list = []) -> None:
        self.mailboxes = mailboxes
        self.allowed_from = {mbx["username"].lower() for mbx in mailboxes}
        self.allowed_domains = set(allowed_domains) 
        if '*' in self.allowed_domains:
            logging.warning("Wildcard '*' in allowed domains, all domains are allowed.")
            logging.warning("This is a security risk, please specify allowed domains or restrict access.")
        else:
            logging.info(f"Allowed domains: {self.allowed_domains}")
    
    async def auth_LOGIN(self, server, arg: list[str]) -> AuthResult:
        if not arg:
            await server.push("501 5.5.4 No mechanism specified")
            return AuthResult(success=False, handled=True)

        mechanism = arg[0].upper()

        if mechanism != 'LOGIN':
            await server.push("504 5.7.4 Unrecognized authentication type")
            return AuthResult(success=False, handled=True)

        username_bytes = await server.challenge_auth('VXNlcm5hbWU6', encode_to_b64=False, log_client_response=False)
        username = username_bytes.decode('utf-8', errors='replace')
        logging.debug("Username received: %s", username)
        password_bytes = await server.challenge_auth('UGFzc3dvcmQ6', encode_to_b64=False, log_client_response=False)
        password = password_bytes.decode('utf-8', errors='replace')
        # logging.debug("Password received: %s", password)
        if check_credentials(username, password):
            logging.info(f"Auth success: {username} from server")
            return AuthResult(success=True, handled=True)
        
        server.push("535 5.7.8 Authentication credentials invalid")
        logging.error(f"Auth failed: {username} from server")
        return AuthResult(success=False, handled=True)
    
    async def auth_PLAIN(self, server, args):
        if len(args) < 2 or args[0] != "PLAIN":
            server.push("501 5.5.4 No mechanism specified")
            return AuthResult(success=False, handled=True, message="Invalid PLAIN data")
        
        parts = base64.b64decode(args[1]).decode('utf-8', 'replace').split('\x00')
        if len(parts) != 3:
            server.push("501 5.5.4 Invalid PLAIN data format")
            return AuthResult(success=False, handled=True, message="Invalid PLAIN data format")
        
        [auth_id, username, password] = parts

        logging.debug(f"AUTH PLAIN: authzid=\"{auth_id}\", user={username}")

        if check_credentials(username, password):
                logging.info(f"Auth success: {username} from server")
                return AuthResult(success=True, handled=True)
            
        return AuthResult(success=False, handled=True)


    async def handle_DATA(self, server, session, envelope):
        try:
            smtp_from = envelope.mail_from.lower()
            _, parsed_smtp_from = parseaddr(smtp_from)
            #self.allowed_domains = set(allowed_domains) 
            rcpt_domains = set([rcpt.split('@')[-1] for rcpt in envelope.rcpt_tos])
            if '*' not in self.allowed_domains:
                denied = rcpt_domains - self.allowed_domains
                if denied:
                    logging.warning(f"Denied recipient domain(s): {denied}")
                    return "550 Recipient domain not allowed"

            msg = BytesParser(policy=policy.default).parsebytes(envelope.original_content)
            _, parsed_header_from = parseaddr(msg.get("From", "").lower())

            if parsed_smtp_from != parsed_header_from:
                logging.warning(f"MAIL FROM ({parsed_smtp_from}) ≠ Header From ({parsed_header_from})")
                return "550 MAIL FROM and From: header mismatch"

            if parsed_header_from not in self.allowed_from:
                logging.warning(f"Sender not allowed: {parsed_header_from}")
                return "550 Sender not allowed"

            logging.info(f"Sending message from {parsed_smtp_from} to {envelope.rcpt_tos}")
            await send_mail(parsed_smtp_from, envelope.rcpt_tos, msg)
            return "250 Message accepted for delivery"

        except Exception:
            logging.exception("Failed to send via Graph")
            return "451 Failed to send message"

class POP3Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.authenticated = False
        self.username = None
        self.messages = []  # (msg_id, size, etag)
        self.uids = []
        self.cache = {}
        self.deleted = set()
        self.wfile.write(b'+OK POP3 Proxy ready\r\n')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                line = self.rfile.readline().decode(errors='ignore\r\n').strip()
                if not line:
                    break
                logging.debug(f" {line if line[:5].upper() not in ['PASS ', 'PLAIN'] else f'{line[:5].strip()} *****'}")

                cmd, *args = line.split()
                cmd = cmd.upper()

                if cmd == "USER":
                    self.username = args[0] if args else None
                    self.wfile.write(b'+OK user accepted\r\n')

                elif cmd == "PASS":
                    if not self.username or not args or not check_credentials(self.username, args[0]):
                        self.wfile.write(b'-ERR invalid credentials\r\n')
                        return
                    try:
                        self.messages = loop.run_until_complete(list_messages(self.username))
                        self.uids = [msg["id"] for msg in self.messages]
                        self.deleted.clear()
                        self.cache.clear()
                        logging.info(f"Retrieved {len(self.messages)} messages for {self.username}")
                    except Exception:
                        logging.error("Failed to retrieve messages")
                        self.wfile.write(b'-ERR failed to list messages\r\n')
                        return
                    self.authenticated = True
                    self.wfile.write(b'+OK auth successful\r\n')

                elif cmd == "STAT":
                    remaining = [msg for i, msg in enumerate(self.messages) if i not in self.deleted]
                    count = len(remaining)
                    total = sum(msg["size"] for msg in remaining)
                    self.wfile.write(f"+OK {count} {total}\r\n".encode())

                elif cmd == "LIST":
                    self.wfile.write(f"+OK {len(self.messages)} messages:\r\n".encode())
                    for i, msg in enumerate(self.messages):
                        if i not in self.deleted:
                            self.wfile.write(f"{i+1} {msg['size']}\r\n".encode())
                    self.wfile.write(b'.\r\n')

                elif cmd == "UIDL":
                    if args:
                        idx = int(args[0]) - 1
                        if 0 <= idx < len(self.uids) and idx not in self.deleted:
                            uid = self.uids[idx]
                            self.wfile.write(f"+OK {idx+1} {uid}\r\n".encode())
                        else:
                            self.wfile.write(b'-ERR no such message\r\n')
                    else:
                        self.wfile.write(f"+OK {len(self.uids)} messages:\r\n".encode())
                        for i, uid in enumerate(self.uids):
                            if i not in self.deleted:
                                self.wfile.write(f"{i+1} {uid}\r\n".encode())
                        self.wfile.write(b'.\r\n')

                elif cmd == "RETR":
                    try:
                        idx = int(args[0]) - 1
                        if idx < 0 or idx >= len(self.messages) or idx in self.deleted:
                            self.wfile.write(b'-ERR no such message\r\n')
                            continue
                        msg_id = self.messages[idx]["id"]
                        if msg_id in self.cache:
                            raw = self.cache[msg_id]
                            logging.debug(f"Using cached message {msg_id}")
                        else:
                            raw = loop.run_until_complete(get_message_raw(self.username, msg_id))
                            self.cache[msg_id] = raw
                            logging.debug(f"Retrieved message {msg_id}")
                        self.wfile.write(b'+OK message follows\r\n')
                        self.wfile.write(raw)
                        self.wfile.write(b'\r\n.\r\n')
                    except Exception:
                        logging.exception("Failed to retrieve message")
                        self.wfile.write(b'-ERR failed to retrieve message\r\n')

                elif cmd == "DELE":
                    try:
                        idx = int(args[0]) - 1
                        if 0 <= idx < len(self.messages):
                            self.deleted.add(idx)
                            self.wfile.write(b'+OK marked for deletion\r\n')
                        else:
                            self.wfile.write(b'-ERR no such message\r\n')
                    except Exception:
                        self.wfile.write(b'-ERR invalid index\r\n')

                elif cmd == "RSET":
                    self.deleted.clear()
                    self.wfile.write(b'+OK\r\n')

                elif cmd == "NOOP":
                    self.wfile.write(b'+OK\r\n')

                elif cmd == "QUIT":
                    if self.deleted:
                        self.wfile.write(b'+OK Deleting marked messages\r\n')
                        for idx in self.deleted:
                            try:
                                msg_id = self.messages[idx]["id"]
                                etag = self.messages[idx].get("etag")
                                loop.run_until_complete(delete_message(self.username, msg_id, etag))
                                logging.info(f"Deleted message {msg_id} for {self.username}")
                            except Exception:
                                logging.error(f"Failed to delete message {self.messages[idx]['id']}")
                    self.wfile.write(b'+OK Bye\r\n')
                    break

                else:
                    self.wfile.write(b'-ERR unknown command\r\n')
        except Exception:
            logging.error("Error in POP3 handler")
        finally:
            if not self.wfile.closed:
                self.wfile.write(b'-ERR closing connection\r\n')
            self.wfile.close()
            loop.close() 
