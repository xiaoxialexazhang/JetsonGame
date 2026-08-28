"""Every API call runs here, off the pygame thread, so the world never freezes.
Workers push (kind, payload) tuples onto a queue that the main loop drains."""
from __future__ import annotations

import queue
import threading
import traceback

RESULTS: "queue.Queue[tuple[str, dict]]" = queue.Queue()


def emit(kind: str, **payload):
    RESULTS.put((kind, payload))


def run(fn, *args, **kwargs):
    """Fire-and-forget a function on a daemon thread."""
    def wrapper():
        try:
            fn(*args, **kwargs)
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            emit("error", message=str(e))

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    return t


def drain():
    """Yield everything currently queued. Call once per frame."""
    while True:
        try:
            yield RESULTS.get_nowait()
        except queue.Empty:
            return
