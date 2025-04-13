# Contributing to m365proxy

Thank you for considering contributing to **m365proxy** – a simple yet powerful mail proxy for Microsoft 365!

I welcome contributions of all kinds: bug reports, improvements, new features, and documentation.

---

## 💡 Getting Started

1. **Fork the repository**  
   https://github.com/sh0rch/m365proxy → Click “Fork”

2. **Clone your fork**

   ```bash
   git clone https://github.com/your-username/m365proxy.git
   cd m365proxy
   ```

3. **Install in editable mode**

   ```bash
   pip install -e .
   ```

4. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

---

## ✍️ Style Guide

- Use **PEP8** formatting (via `black`)
- Run `ruff` or `flake8` to catch common issues
- Keep functions and modules clean and focused
- Write meaningful **commit messages**

---

## 📂 Project Structure

```
m365proxy/
│
├── __main__.py              # CLI entry point
├── auth.py                  # Token auth logic
├── cli.py                   # Command line interface
├── proxies.py               # Handlers for SMTP/POP3
├── graph_api.py             # Graph API decorators and helpers
│── config.py                # Config loader/validator
├── configure.py             # Config file generators
├── mail.py                  # SMTP/POP3 handlers via GraphAPI


```

---

## 📦 Submitting a Pull Request

1. Create a new branch:

   ```bash
   git checkout -b fix/describe-issue
   ```

2. Make your changes and commit them:

   ```bash
   git commit -m "Fix: short description of the fix"
   ```

3. Push your branch:

   ```bash
   git push origin fix/describe-issue
   ```

4. Open a pull request on GitHub and describe what you changed.

---

## 🛡️ Security Policy

Please **do not** report security issues publicly.  
Instead, email the maintainer directly: `sh0rch@iwl.dev`

---

## 🙌 Thanks for Contributing!

Your feedback and code help make this project better for everyone.  
If you have any questions, feel free to reach out!
