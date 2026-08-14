"""Worker process entrypoint with signal handling and graceful drain."""

from __future__ import annotations

import logging
import signal
import sys
from threading import Event

from veri_kalitesi.jobs.settings import PersistentJobSettings
from veri_kalitesi.operational_logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Worker sürecini başlat; SIGTERM/SIGINT ile kontrollü kapatma."""

    configure_logging()
    settings = PersistentJobSettings.from_environment()
    from veri_kalitesi.jobs.production import create_production_worker

    runtime = create_production_worker(settings)
    stop_event = Event()

    def _request_stop(signum: int, _frame: object) -> None:
        logger.info("Worker received signal %s, draining…", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    try:
        runtime.worker.run_forever(
            stop_event,
            idle_wait_seconds=settings.idle_wait_seconds,
        )
    except Exception:
        logger.exception("Worker terminated with error.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
