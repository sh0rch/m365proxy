# m365proxy - Docker Image

Transparent SMTP/POP3 proxy for Microsoft 365 using Microsoft Graph API.

## 🐳 Quick Start

```bash
docker run -d \
  -v $(pwd)/config:/config \
  -v $(pwd)/queue:/app/queue \
  -p 10025:10025 -p 10110:10110 -p 10465:10465 -p 10995:10995 \
  --env-file .env \
  sh0rch/m365proxy:latest
```

## ⚙️ Configuration

- `config.json` and `tokens.enc` must be placed in the `./config` directory.
- Mail queue will be written to `./queue`.

## 🔐 First-time Setup (Interactive)

```bash
docker run --rm -it -v $(pwd)/config:/config sh0rch/m365proxy configure
docker run --rm -it -v $(pwd)/config:/config sh0rch/m365proxy login
```

## 🛠 Environment

- Based on `python:3.11-slim`
- Supports STARTTLS, SMTPS, POP3S

## 📂 Volumes

- `/config` → contains config and token files
- `/app/queue` → stores pending email queue

## 💬 Example Use Cases

- Sending and receiving mail from embedded devices
- Secure scan-to-email over Microsoft 365
- Bridging legacy systems to modern cloud mail APIs

## 📤 GitHub & Source

[https://github.com/sh0rch/m365proxy](https://github.com/sh0rch/m365proxy)
