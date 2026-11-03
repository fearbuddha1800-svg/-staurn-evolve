---
slug: relay_main
type: note
graph: gitnexus
---

"""Signal-relay standalone executable entry point.

Bundles the Telegram signal daemon + MT5 position manager into one .exe.
Usage: signal_relay.exe [--login | --list-dialogs]
"""
import asyncio
import os
import sys
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import daemon  # noqa: E402
from manage import main as manage_main  # noqa: E402


def _run_manage():
    try:
        manage_main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"[manager] stopped: {e}")


def main():
    args = sys.argv[1:]
    if "--login" in args or "--list-dialogs" in args:
        daemon.main()
        return

    print("signal-relay: starting daemon + MT5 manager...")

    # Start manage.py position manager in a background daemon thread
    mgr_thread = threading.Thread(target=_run_manage, daemon=True)
    mgr_thread.start()

    # Run the Telegram daemon serve loop in the main thread (blocking)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        print("\nsignal-relay: shutting down...")
    except SystemExit:
        pass


if __name__ == "__main__":
    main()

