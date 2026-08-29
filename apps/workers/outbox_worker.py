"""
Mandate Gateway — Outbox Worker Process Entrypoint
Section M09 — Production Platform & Outbox Worker Separation
"""

from __future__ import annotations

import asyncio
import signal
from typing import Sequence

from db.models.outbox import OutboxEventModel
from db.session import get_async_session_factory
from db.unit_of_work import AsyncUnitOfWork

import logging

logger = logging.getLogger("mandate_gateway.outbox_worker")


class OutboxWorker:
    """
    Independent worker process for fetching and processing pending Outbox events.
    Enforces at-least-once delivery semantics without keeping long database transactions open.
    """

    def __init__(self, batch_size: int = 50, poll_interval_seconds: float = 2.0) -> None:
        self.batch_size = batch_size
        self.poll_interval_seconds = poll_interval_seconds
        self.running = False

    async def process_batch(self) -> int:
        """Fetch and dispatch a batch of pending outbox events."""
        session_factory = get_async_session_factory()
        if session_factory is None:
            return 0

        processed_count = 0
        async with AsyncUnitOfWork(session_factory) as uow:
            pending_events: Sequence[OutboxEventModel] = await uow.outbox.get_pending_events(
                limit=self.batch_size
            )
            if not pending_events:
                return 0

            for event in pending_events:
                try:
                    logger.info(
                        f"Outbox event dispatching: id={event.outbox_id}, type={event.event_type}",
                        extra={
                            "outbox_event_id": event.outbox_id,
                            "event_type": event.event_type,
                            "aggregate_id": event.aggregate_id,
                        },
                    )
                    await uow.outbox.mark_dispatched(event.outbox_id)
                    processed_count += 1
                except Exception as err:
                    logger.error(
                        f"Outbox event dispatch failure: id={event.outbox_id}, err={err}",
                        extra={"outbox_event_id": event.outbox_id},
                    )
                    await uow.outbox.mark_failed(event.outbox_id)

            await uow.commit()
        return processed_count

    async def run(self) -> None:
        """Run continuous worker loop until stopped."""
        self.running = True
        logger.info("Outbox worker process started.")
        while self.running:
            try:
                count = await self.process_batch()
                if count == 0:
                    await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.error(f"Error in outbox worker loop: {err}")
                await asyncio.sleep(self.poll_interval_seconds)
        logger.info("Outbox worker process stopped cleanly.")

    def stop(self) -> None:
        """Signal worker to stop running."""
        self.running = False


async def _main() -> None:
    worker = OutboxWorker()

    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        logger.info("Received termination signal. Shutting down outbox worker...")
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # Signal handlers might not be supported on non-POSIX platforms

    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
