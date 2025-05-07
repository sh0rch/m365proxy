# m365proxy - Lightweight Microsoft 365 Mail Proxy

Transparent SMTP/POP3 proxy for Microsoft 365 using Microsoft Graph API.
Supports STARTTLS, SMTPS, POP3S and shared mailboxes.

---

## 🐳 Quick Start (Recommended)

Use the provided install script to configure and launch:

```bash
curl -O https://raw.githubusercontent.com/sh0rch/m365proxy/main/install.sh
chmod +x install.sh
./install.sh
```

This script will:

- Pull the latest Docker image
- Run interactive `configure` and `login`
- Start the container with proper volume bindings

---

## 📦 Manual Docker Usage

### Initial configuration:

```bash
docker run --rm -it -v $(pwd)/config:/config sh0rch/m365proxy configure
docker run --rm -it -v $(pwd)/config:/config sh0rch/m365proxy login
```

### Run server:

```bash
docker run -d \
  --name m365proxy \
  -v $(pwd)/config:/config \
  -v $(pwd)/queue:/app/queue \
  -p 1025:1025 -p 110:110 -p 465:465 -p 995:995 \
  sh0rch/m365proxy:latest
```

---

## 📂 Volumes

- `/config` → Contains `config.json`, `tokens.enc`
- `/app/queue` → Stores queued mail data

---

## 💡 Common Use Cases

- Scan-to-email over M365
- POP3/SMTP access for legacy systems
- Secure proxy for embedded or shared devices

---

Source: [https://github.com/sh0rch/m365proxy](https://github.com/sh0rch/m365proxy)
