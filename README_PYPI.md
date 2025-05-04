
# SMTP & POP3 Proxy for Microsoft 365 Shared Mailboxes

[![PyPI version](https://img.shields.io/pypi/v/m365proxy.svg)](https://pypi.org/project/m365proxy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Repo](https://img.shields.io/badge/GitHub-sh0rch%2Fm365proxy-blue)](https://github.com/sh0rch/m365proxy)

## Why This Project?

Many legacy systems, embedded devices, and applications:

- ❌ Do not support OAuth2 for sending or receiving email
- ❌ Cannot access Microsoft 365 endpoints directly due to network restrictions
- ❌ Require SMTP/POP3 and basic username/password authentication

This proxy provides a **secure bridge** between those tools and Microsoft 365:

- 🛡️ Messages are relayed through a single authenticated Microsoft 365 account
- 🔐 Only authorized clients (defined in config) can use the proxy
- 🌍 Useful when you can't expose your own mail servers in SPF records
- 📥 Enables retrieval of mail from shared mailboxes via POP3
- 💸 With a single low-cost **Exchange Online Kiosk license** + free **shared mailboxes**, you can build a distributed, multi-sender notification system — without a full SMTP infrastructure

Ideal for:

- Network monitoring software
- Firewalls, routers, printers, IP cameras
- IoT and industrial equipment
- Legacy on-prem systems
- Environments with no internet access or firewall egress rules

This tool helps consolidate notifications from many devices and subsystems under one tenant, while still keeping SPF clean.

---

## ✨ Features

- ✅ Full async SMTP/POP3 proxy
- ✅ Microsoft Graph API integration (sendMail, get messages)
- ✅ Shared mailbox support
- ✅ OAuth2 Device Flow authentication
- ✅ Encrypted token storage
- ✅ Built-in mail queue (for offline mode)
- ✅ Automatic resend when connection restored
- ✅ Linux and Windows support
- ✅ Drop-in SMTP/POP3 replacement

---

## 🚀 Quick Start

```bash
pip install m365proxy

# First-time login to Microsoft 365 via Device Flow
m365proxy --login

# Start the proxy (SMTP + POP3)
m365proxy run
```

---

## 🛠 Configuration (`config.json`)

Example:

```json
{
  "user": "admin@tenant.onmicrosoft.com",
  "client_id": "YOUR-APP-ID",
  "tenant_id": "YOUR-TENANT-ID",
  "mailboxes": [
    { "username": "alerts@tenant.onmicrosoft.com", "password": "secret" }
  ],
  "bind": "127.0.0.1",
  "smtp_port": 2525,
  "pop3_port": 110,
  "tls": {
    "tls_cert": "cert.pem",
    "tls_key": "key.pem"
  },
  "attachment_limit_mb": 80
}
```

---

## 📦 Offline Mode & Queue

When Microsoft 365 is unreachable:

- ✉️ Messages are **queued to disk**
- 🔄 Automatically retried in background (every 5 minutes)
- 🧊 No data loss — even if the device is offline for hours

You can inspect the queue at:

```bash
ls ~/.m365proxy/queue/
```

---

## 📡 Architecture

```
  Legacy Device (SMTP) ─────┐
                            ├─> SMTP Proxy ──> Graph API ──> Exchange Mailbox
  App / Printer / Camera ──┘

  POP3 Client <────────────── POP3 Proxy <─── Graph API (Shared Mail)
```

---

## 🪪 Licensing

MIT © sh0rch • See LICENSE

---


---

# 📦 Changelog — m365proxy

## [1.2.0] - 2025-05-04

### ✨ New Features

- **Fully asynchronous SMTP and POP3 proxy**
  - The proxy server is now built entirely on `asyncio`, allowing non-blocking performance and better concurrency.
- **SMTP queue and offline resend support**
  - Outgoing messages are stored on disk and retried automatically when Graph API becomes reachable.
- **HTTPS proxy support via `HTTPS_PROXY` environment variable**
  - Enables deployment behind corporate or cloud proxies.
- **Safe resend without duplication**
  - The queue system is aware of delivery status to prevent double-sending.
- **AUTH PLAIN and AUTH LOGIN for POP3**
  - Compatible with Outlook, Thunderbird, and other standard clients.

### 🔧 Improvements

- Improved logging of network/API failures
- Graph API 405/403 responses treated as valid reachability indicators
- Added architectural diagram and offline-mode documentation
- Enhanced `README.md` with structured features and examples
- Initial `docs/` folder with `mkdocs.yml` and Markdown pages

### ⚠️ Upgrade Notes

- Python 3.9 or higher is recommended
- `start_smtp_server()` is now async and must be awaited
- Queue processing and token refresh now run as background tasks

---

MIT © 2025 [sh0rch](https://github.com/sh0rch)
