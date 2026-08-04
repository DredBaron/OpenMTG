import itertools
import logging
import threading
import time
from enum import IntEnum
from queue import PriorityQueue
import constants
import httpx
from constants import API_RATES

logger = logging.getLogger(__name__)

RATE_LIMIT_RPS = float(API_RATES['RATE_LIMIT_RPS'])
RATE_LIMIT_GAP = float(API_RATES['RATE_LIMIT_GAP'])
ERROR_429_BACKOFF = int(API_RATES['ERROR_429_BACKOFF'])
CALLER_TIMEOUT = int(API_RATES['CALLER_TIMEOUT'])

class Priority(IntEnum):
    USER       = 0      # Frontend
    BACKGROUND = 1      # Backend

class _Request:
    _counter = itertools.count()

    def __init__(
        self,
        url:          str,
        params:       dict | None,
        result:       list,
        event:        threading.Event,
        method:       str = 'GET',
        body:         dict | None = None,
        http_timeout: float = 10.0,
    ) -> None:
        self.seq          = next(self._counter)
        self.url          = url
        self.params       = params
        self.body         = body
        self.method       = method
        self.http_timeout = http_timeout
        self.result       = result
        self.event        = event

class ScryfallQueue:

    _instance: "ScryfallQueue | None" = None
    _init_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ScryfallQueue":
        with cls._init_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._setup()
                cls._instance = obj
        return cls._instance

    def _setup(self) -> None:
        self._client = httpx.Client(
            timeout=10,
            headers={
                "User-Agent": (
                    f"OpenMTG/{constants.VERSIONS['API_VERSION']}"
                    " (https://github.com/DredBaron/OpenMTG)"
                ),
                "Accept": "application/json",
            },
        )
        self._queue: PriorityQueue = PriorityQueue()
        self._last_sent: float = 0.0

        worker = threading.Thread(
            target=self._worker,
            daemon=True,
            name="scryfall-queue",
        )
        worker.start()
        logger.info(
            f"ScryfallQueue started - "
            f"{RATE_LIMIT_RPS} req/s ({RATE_LIMIT_GAP * 1000:.0f} ms gap), "
            f"429 backoff {ERROR_429_BACKOFF:.0f}s"
        )

    def _worker(self) -> None:
        while True:
            priority, _seq, req = self._queue.get()

            gap = RATE_LIMIT_GAP - (time.monotonic() - self._last_sent)
            if gap > 0:
                time.sleep(gap)

            response: httpx.Response | None = None
            try:
                if req.method == 'POST':
                    response = self._client.post(req.url, json=req.body, timeout=req.http_timeout)
                else:
                    response = self._client.get(req.url, params=req.params, timeout=req.http_timeout)
                self._last_sent = time.monotonic()

                if response.status_code == 429:
                    logger.warning(
                        f"Scryfall 429 received, backing off {ERROR_429_BACKOFF:.0f}s "
                        f"then retrying {req.url}"
                    )
                    time.sleep(ERROR_429_BACKOFF)
                    self._queue.put((priority, req.seq, req))
                    continue

            except Exception as exc:
                logger.error(f"ScryfallQueue request error ({req.url}): {exc}")

            req.result.append(response)
            req.event.set()

    def get(
        self,
        url: str,
        params: dict | None = None,
        priority: Priority = Priority.USER,
        timeout: float = CALLER_TIMEOUT,
    ) -> httpx.Response | None:
        result: list[httpx.Response | None] = []
        event  = threading.Event()
        req    = _Request(url, params, result, event)

        queue_depth = self._queue.qsize()
        if queue_depth > 10:
            logger.debug(f"ScryfallQueue depth={queue_depth} priority={priority.name}")

        self._queue.put((int(priority), req.seq, req))

        if not event.wait(timeout=timeout):
            logger.warning(
                f"ScryfallQueue timeout ({timeout}s) waiting for {url} "
                f"[priority={priority.name}]"
            )
            return None

        return result[0] if result else None

    def post(
        self,
        url:          str,
        body:         dict | None = None,
        priority:     Priority = Priority.USER,
        timeout:      float = CALLER_TIMEOUT,
        http_timeout: float = 30.0,
    ) -> httpx.Response | None:
        result: list[httpx.Response | None] = []
        event  = threading.Event()
        req    = _Request(url, None, result, event, method='POST', body=body, http_timeout=http_timeout)

        self._queue.put((int(priority), req.seq, req))

        if not event.wait(timeout=timeout):
            logger.warning(
                f"ScryfallQueue timeout ({timeout}s) waiting for POST {url}"
            )
            return None

        return result[0] if result else None

    def qsize(self) -> int:
        return self._queue.qsize()

scryfall_queue = ScryfallQueue()