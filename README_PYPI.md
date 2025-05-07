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

## ✨ New Features (v2)

- 🆕 **POP3 STARTTLS support** — mail clients can now upgrade plaintext POP3 connections to TLS securely
- 🆕 **SMTP SMTPS support (TLS from start)** — SMTPS (port 465) is now supported in addition to STARTTLS (port 587 or custom)
- 🆕 **POP3S support (TLS from start)** — full support for POP3 over SSL/TLS (port 995)
- 🔁 **Simultaneous operation of all modes** — you can now run:
  - SMTP (with STARTTLS)
  - SMTPS (SSL/TLS)
  - POP3 (with STARTTLS)
  - POP3S (SSL/TLS)
    …on different ports, either individually or together
- 🛠 **Improved configuration parser**:
  - Clearer validation of TLS, ports, logging paths, and mailbox entries
  - Prevents conflicts like `smtp_port == smtps_port`
  - Enhanced proxy URL formatting and diagnostics
- 🤝 **Better compatibility** with popular clients and devices:
  - Thunderbird, Outlook, MFDs, embedded IoT mailers, etc.
- ✅ **Final release for this stage** — future possibilities (IMAP, shared calendars, folders) may push the project into enterprise mail territory, which goes beyond the scope and potentially conflicts with Microsoft licensing — and that’s not a direction this project is taking.

## Overview

This tool is designed for cases where you want to use real mail clients and devices (like scan-to-email from printers or backup software) with Microsoft 365 but want to avoid exposing user credentials or managing OAuth2 flows manually.

It provides local endpoints (SMTP and POP3) that forward requests securely via Microsoft Graph.

## Features

- ✅ Transparent mail sending via Microsoft Graph `/sendMail`
- ✅ Works with shared mailboxes ("Send As")
- ✅ Supports large attachments (up to 150MB via Graph API chunked upload)
- ✅ POP3 receiving, with folder selection and message flags
- ✅ Shared folder access for POP3 download (e.g. service@domain.com)
- ✅ STARTTLS and SMTPS support
- ✅ Multiple mailboxes with independent credentials
- ✅ Authenticated and secure
- ✅ Python-based and container-ready

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
