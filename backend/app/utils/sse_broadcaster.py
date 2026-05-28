import logging
import asyncio
import json
import math

from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import Request
from fastapi.responses import StreamingResponse


logger = logging.getLogger(__name__)


def sanitize_for_json(value: Any):
    """Make any Python object JSON-serializable in a safe way."""
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return None
    if isinstance(value, dict):
        return {str(sanitize_for_json(k)): sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(v) for v in value]
    try:
        return str(value)
    except Exception:
        return None

def format_sse_event(event_type: str | None, data: Any) -> str:
    """
    Format an SSE event with optional named event type.
    If event_type is None, emits only 'data: ...' lines.
    """
    payload = sanitize_for_json(data)
    body = json.dumps(payload, ensure_ascii=False)
    if event_type:
        return f"event: {event_type}\ndata: {body}\n\n"
    else:
        return f"data: {body}\n\n"


class SSEBroadcaster:
    """
    Generic SSE broadcaster for FastAPI.

    Usage pattern:
      - Initialize with request and base metadata.
      - Call run(producer) where producer calls publish() to emit events.
      - run() returns a StreamingResponse.
    """

    def __init__(
        self,
        request: Request,
        base_event: Dict[str, Any] | None = None,
        queue_maxsize: int = 100,
    ):
        self.request = request
        self.base_event = base_event or {}
        self.queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=queue_maxsize)
        self.disconnected_event = asyncio.Event()
        self.event_seq = 0
        self._producer_task: Optional[asyncio.Task] = None

    async def publish(
        self,
        event_type: str,
        payload: Dict[str, Any] | None = None,
        status: str | None = None,
    ) -> bool:
        if self.disconnected_event.is_set() or await self.request.is_disconnected():
            self.disconnected_event.set()
            logger.debug("Client disconnected before emitting %s event", event_type)
            return False

        # Start from base_event only
        event_data: Dict[str, Any] = dict(self.base_event)

        if status:
            event_data["status"] = status

        if payload is not None:
            event_data["payload"] = payload

        try:
            await asyncio.wait_for(self.queue.put({"type": event_type, "data": event_data}), timeout=1.0)
        except asyncio.TimeoutError:
            if self.disconnected_event.is_set() or await self.request.is_disconnected():
                self.disconnected_event.set()
                return False
            logger.warning("SSE queue is full; dropping event %s", event_type)
            return False

        return True


    async def _event_generator(self):
        try:
            while True:
                try:
                    event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Exit if producer is done or client disconnected
                    if self.disconnected_event.is_set() or (self._producer_task and self._producer_task.done()):
                        break
                    continue

                yield format_sse_event(event["type"], event["data"])

                if event["type"] == "done":
                    break

                if await self.request.is_disconnected():
                    self.disconnected_event.set()
                    logger.info("Client disconnected from SSE stream")
                    break
        except asyncio.CancelledError:
            self.disconnected_event.set()
            logger.info("Client disconnected from SSE stream (cancelled)")
            raise
        finally:
            if self._producer_task and not self._producer_task.done():
                self._producer_task.cancel()
            if self._producer_task:
                try:
                    await self._producer_task
                except asyncio.CancelledError:
                    pass

    def run(
        self,
        producer: Callable[[Callable[..., Awaitable[bool]]], Awaitable[None]],
        headers: Dict[str, str] | None = None,
    ) -> StreamingResponse:
        """
        Start the producer and return a StreamingResponse.

        producer(publish_fn) is an async function that:
          - calls await publish_fn(event_type, payload, status, extras)
          - typically emits multiple events and finally a 'done' event
        """

        async def _producer_wrapper():
            try:
                await producer(self.publish)
            except Exception as exc:
                logger.error("SSE producer raised an exception", exc_info=exc)
                # Optionally emit an error event
                await self.publish(
                    "error",
                    {"message": "Internal SSE producer error", "status": 500},
                    status="Failed",
                )
            finally:
                if not self.disconnected_event.is_set():
                    await self.publish("done", None, status="Completed")

        self._producer_task = asyncio.create_task(_producer_wrapper())

        response_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if headers:
            response_headers.update(headers)

        return StreamingResponse(
            self._event_generator(),
            media_type="text/event-stream",
            headers=response_headers,
        )
