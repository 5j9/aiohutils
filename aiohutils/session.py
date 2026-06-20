from collections.abc import Callable
from typing import Unpack
from warnings import deprecated

from aiohttp import (
    ClientResponse,
    ClientSession,
    ClientTimeout,
    TCPConnector,
    ThreadedResolver,
)
from aiohttp.client import _RequestOptions

from aiohutils import logger as _logger

_warned = set()


class SessionManager:
    __slots__ = (
        '_session',
        'client_session_kwargs',
        'connector',
        'timeout',
    )

    def __init__(
        self,
        connector: Callable[[], TCPConnector | None] = lambda: TCPConnector(
            ttl_dns_cache=60 * 60 * 24, resolver=ThreadedResolver()
        ),
        timeout: ClientTimeout = ClientTimeout(total=60.0, sock_connect=30.0),
        **client_session_kwargs,
    ):
        self.connector = connector
        self.timeout = timeout
        self.client_session_kwargs = client_session_kwargs
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        session = self._session
        if session is not None:
            return session
        session = self._session = ClientSession(
            connector=self.connector(),
            timeout=self.timeout,
            **self.client_session_kwargs,
        )
        return session

    async def close(self):
        session = self._session
        if session is not None:
            await session.close()

    @staticmethod
    def _check_response(response: ClientResponse):
        response.raise_for_status()
        if not (hist := response.history):
            return
        if (url := str(response.url)) in _warned:
            return
        _logger.warning(f'redirection from {hist[0].url} to {url}')
        _warned.add(url)

    async def request(
        self,
        method: str,
        url: str,
        *args,
        retry: int = 3,
        **kwargs: Unpack[_RequestOptions],
    ) -> ClientResponse:
        while True:
            try:
                resp = await self.session.request(method, url, *args, **kwargs)
                self._check_response(resp)
                return resp
            except OSError:
                retry -= 1
                if retry >= 0:
                    continue
                raise

    @deprecated('use self.request("get", ...) instead')
    async def get(self, *args, retry=3, **kwargs) -> ClientResponse:
        return await self.request('get', *args, retry=retry - 1, **kwargs)
