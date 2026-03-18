import asyncio
import time
from typing import Callable, Coroutine, Any

class AsyncDebouncer:
    """
    Debounces an async function, ensuring it is called at most once every `delay` seconds.
    If multiple calls are made within the delay period, the latest arguments are used
    for the single execution at the end of the window.
    """
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self._task: asyncio.Task | None = None
        self._last_execution_time = 0.0
        self._func: Callable[..., Coroutine[Any, Any, Any]] | None = None
        self._latest_args = ()
        self._latest_kwargs = {}

    def __call__(self, func: Callable[..., Coroutine[Any, Any, Any]]):
        async def wrapper(*args, **kwargs):
            self._func = func
            self._latest_args = args
            self._latest_kwargs = kwargs

            now = time.time()
            time_since_last_run = now - self._last_execution_time

            if self._task and not self._task.done():
                self._task.cancel()

            # If enough time has passed, execute immediately
            if time_since_last_run >= self.delay:
                self._last_execution_time = now
                try:
                    await self._func(*self._latest_args, **self._latest_kwargs)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Debounced function error: {e}")
                return

            # Otherwise, schedule a new task
            self._task = asyncio.create_task(self._wait_and_execute(self.delay))

        return wrapper

    async def _wait_and_execute(self, wait_time: float):
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            return
            
        self._last_execution_time = time.time()
        if self._func:
            try:
                await self._func(*self._latest_args, **self._latest_kwargs)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Debounced function error: {e}")
