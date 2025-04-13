# -----------------------------------------------------------------------------
# m365proxy - Lightweight Microsoft 365 SMTP/POP3 proxy over Graph API
# https://pypi.org/project/m365proxy
#
# Copyright (c) 2025 sh0rch
# Licensed under the MIT License: https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------

import asyncio
import logging
from m365proxy.cli import main

def run():
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, shutting down...")
        return 0
    except Exception:
        logging.exception("Unhandled exception in main loop")
        return 1

if __name__ == "__main__":
    raise SystemExit(run())