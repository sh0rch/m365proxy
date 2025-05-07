# Contributing Guide

Thank you for considering contributing to this project!

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/sh0rch/m365proxy.git
   cd m365proxy
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Style Guide

Code should follow [PEP8](https://www.python.org/dev/peps/pep-0008/) and be formatted using `autopep8`.

Linting is handled via `flake8`, and additional warnings (such as argument ordering issues) are caught using `flake8-bugbear`.

## ✅ Pre-commit Hooks

This project uses [`pre-commit`](https://pre-commit.com/) to automatically format code and check for common issues before each commit.

### 🔧 Install hooks locally

After cloning the repo and installing dev dependencies:

```bash
pre-commit install
```

This sets up git hooks to run auto-formatters (`autopep8`) and linters (`flake8`, including `flake8-bugbear`) before each commit.

You can also run it manually on all files:

```bash
pre-commit run --all-files
```

### 🧪 What it checks

- Ensures code is formatted according to PEP8
- Prevents common bugs (like bad argument order with `*args`)
- Keeps your diffs clean and consistent

If you don’t want to use it, you can simply skip installation or uninstall with:

```bash
pre-commit uninstall
```

Pre-commit config is stored in `.pre-commit-config.yaml` and may be safely removed from the project if unused.

## Submitting Changes

- Fork the repository and create a new branch for your changes.
- Make sure the code passes all tests and pre-commit checks.
- Submit a pull request with a clear description of what you changed and why.

---

Thank you for contributing! 🎉
We appreciate your help in making this project better for everyone. If you have any questions or need assistance, feel free to reach out.
