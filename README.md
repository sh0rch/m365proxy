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

This tool helps consolidate notifications from many devices and subsystems under one tenant, while still keeping SPF/DKIM/DMARC compliant and not exposing internal systems.

---

## 🐍 Installation

To install the proxy as a Python package:

```bash
pip install m365proxy
```

You can then run it via:

```bash
m365proxy
```

Or:

```bash
python -m m365proxy
```

---

## Usage

```bash
python -m m365proxy [options]
python -m m365proxy [-config CONFIG] [command]
```

Simple SMTP and POP3 mail proxy to Microsoft 365 mailbox over HTTPS (using Microsoft Graph API).

### Options

| Option             | Description                                                                          |
| ------------------ | ------------------------------------------------------------------------------------ |
| `-h`, `--help`     | Show help message and exit                                                           |
| `-config CONFIG`   | Path to configuration file (default: `<home_folder>/.m365proxy/config.json`)         |
| `-token TOKEN`     | Path to token file (default: `<config_folder>/tokens.enc`)                           |
| `-log-file PATH`   | Log file path (default: `<config_folder>/m365.log`)                                  |
| `-log-level LEVEL` | Logging level for file. One of `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `-bind ADDRESS`    | Bind address for services (default: `127.0.0.1`)                                     |
| `-smtp-port PORT`  | SMTP listening port (default: `10025`)                                               |
| `-pop3-port PORT`  | POP3 listening port (optional, default: `None`)                                      |
| `-https-proxy URL` | HTTPS proxy URL (e.g. `http://proxy.local:3128`)                                     |
| `-no-ssl`          | Disable SSL/TLS for SMTP and POP3                                                    |
| `-debug`           | Enable verbose output (CLI only)                                                     |
| `-quiet`           | Suppress all output except errors (CLI only)                                         |

---

### Commands

| Command        | Description                            |
| -------------- | -------------------------------------- |
| _(none)_       | Start SMTP/POP3 proxy server           |
| `init-config`  | Create minimal default `config.json`   |
| `configure`    | Run interactive configuration          |
| `login`        | Start Microsoft device code login flow |
| `check-token`  | Check current token validity           |
| `show-token`   | Show contents of decrypted token       |
| `check-config` | Show effective configuration           |
| `test`         | Send a test email                      |
| `hash`         | Hash password for use in `config.json` |

> 📌 `hash` requires an argument: the plain password to be hashed.

---

### Examples

```bash
# Start the proxy with default config
python -m m365proxy

# Generate default config file
python -m m365proxy init-config

# Configure interactively
python -m m365proxy configure

# Login via Microsoft device code flow
python -m m365proxy login

# Start the proxy on custom SMTP port and bind to all interfaces
python -m m365proxy -smtp-port 2525 -bind 0.0.0.0

# Run with custom config and token paths in quiet mode
python -m m365proxy -config ./myconfig.json -token /tmp/mytoken.enc -quiet

# Run with detailed logging
python -m m365proxy -config /tmp/myconfig.json -token /tmp/mytoken.enc -log-file /tmp/m365.log -log-level DEBUG
```

---

## 🐳 Docker

Here’s how to run `m365proxy` in a container:

**Dockerfile:**

```Dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install the proxy from PyPI
RUN pip install m365proxy

# Copy configuration files
COPY config.json .
COPY tokens.enc .

# Expose required ports
EXPOSE 10025 10110

CMD ["m365proxy"]
```

**Run example:**

```bash
docker run -d \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/tokens.enc:/app/tokens.enc \
  -p 10025:10025 -p 10110:10110 \
  m365proxy
```

> 🛠 You can also override config or token paths with `-config` and `-token` arguments.

## 🪟 Windows Task Scheduler

To auto-start the proxy on Windows:

1. Open **Task Scheduler**
2. Choose **Create Basic Task**
3. Trigger: _At startup_ or _Log on_
4. Action: _Start a program_
5. Set `Program/script:` to:
   ```text
   pythonw
   ```
   Set `Add arguments:` to:
   ```text
   -m m365proxy -quiet
   ```
   Or, if using the bundled `EXE`, point directly to `m365proxy.exe`.

## 🐧 systemd (Linux Autostart)

To run the proxy as a background service on Linux, create a systemd unit file:

**/etc/systemd/system/m365proxy.service**

```ini
[Unit]
Description=Microsoft 365 Mail Proxy
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m m365proxy -quiet
WorkingDirectory=/opt/m365proxy
Restart=always
User=nobody
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable m365proxy
sudo systemctl start m365proxy
```

---

## Sample Configuration (`config.json`)

```json
{
  "user": "licensed@example.com",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenant_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "allowed_domains": ["example.com"],
  "mailboxes": [
    {
      "username": "shared1@example.com",
      "password": "hashed-secret1"
    },
    {
      "username": "shared2@example.com",
      "password": "hashed-secret2"
    }
  ],
  "bind": "127.0.0.1",
  "smtp_port": 10025,
  "pop3_port": 10110,
  "https_proxy": {
    "url": "http://proxy.local:3128",
    "user": "proxyuser",
    "password": "proxypass"
  },
  "logging": {
    "level": "INFO"
  }
}
```

> 🔐 All passwords hashed and stored locally.

---

## Azure AD / Entra ID Setup

To use Microsoft Graph API, you must register your application in Microsoft Entra ID (Azure Active Directory).

### 1. Register Your App

- Go to [https://entra.microsoft.com](https://entra.microsoft.com)
- Navigate to **Azure Active Directory → App registrations → New registration**
- Set a name like `smtp-proxy`, leave redirect URI empty (device code flow doesn't require it)

### 2. Save Credentials

- Copy the **Client ID** and **Tenant ID** into your `config.json`

### 3. Configure Permissions

- Go to **API permissions → Add a permission → Microsoft Graph → Delegated**
- Add:
  - `Mail.Send` (required, for outgoing mail)
  - `Mail.Send.Shared` (required, for outgoing mail)
  - `Mail.ReadWrite` (optional, for incoming mail)
  - `Mail.ReadWrite.Shared` (optional, for incoming mail)
  - `offline_access` (required, for refresh tokens)
- Grant admin consent for your tenant

### 4. Enable Public Client Flow

- Go to **Authentication → Enable public client (mobile & desktop)**
- Allow **device code flow**

### 5. Authorize the Proxy

- Run the proxy with `login`
- You will be prompted to sign in once in a browser
- After that, tokens will be refreshed automatically

---

# Shared Mailbox Configuration

To send or receive mail on behalf of shared addresses:

- Go to Microsoft 365 Admin Center → Shared mailboxes → Create
- Assign Send As or Send on Behalf rights to your user in the config

**Grant Send As Rights (PowerShell):**

```powershell
Add-RecipientPermission -Identity shared@domain.com -Trustee user@domain.com -AccessRights SendAs
```

**Grant Send on Behalf:**

```powershell
Set-Mailbox shared@domain.com -GrantSendOnBehalfTo user@domain.com
```

📌 **Send As** is preferred for compatibility.

Shared mailboxes do not require licenses and can be used for routing, monitoring, and distribution identities.

---

### Additional Permissions for POP3 Access

To **read or delete messages** from shared mailboxes using the POP3 proxy, you must add the following delegated Microsoft Graph API permissions to your app:

- `Mail.ReadWrite`
- `Mail.ReadWrite.Shared`

These permissions allow the proxy to fetch and delete messages on behalf of the user or shared mailbox.

> 🛡️ Without `Mail.ReadWrite` the proxy will not be able to mark or delete messages after downloading, which may result in repeated deliveries.

> ✅ Admin consent is required for these permissions.

---

### Disabling POP3 (Optional)

If your use case does **not require access to incoming mail**, you can disable POP3 entirely:

```json
{
  "pop3_port": null
}
```

> 🔕 This prevents the proxy from exposing any POP3 service.

---

## Notes

- All outgoing messages use the address specified in `MAIL FROM:`.
- The proxy preserves full message structure: subject, HTML, attachments.
- Attachments are limited to 80MB by default (adjustable).
- All allowed users are declared in `mailboxes[]`.
- SMTP/POP3 clients must authenticate using one of the defined `username/password` combinations.
- POP3 supports UIDL to avoid downloading duplicates.

---

## License

MIT — Author: `sh0rch`
