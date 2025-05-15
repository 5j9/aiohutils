import asyncio
import atexit
from collections.abc import Callable
from logging import warning

from aiohttp import (
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ServerDisconnectedError,
    TCPConnector,
)

_warned = set()


class SessionManager:
    __slots__ = ('_args', '_connector', '_kwargs', '_session')

    def __init__(
        self,
        *args,
        connector: Callable[[], TCPConnector | None] = lambda: None,
        **kwargs,
    ):
        self._args = args
        self._connector = connector

        self._kwargs = {
            'timeout': ClientTimeout(
                total=60.0, sock_connect=30.0, sock_read=30.0
            ),
        } | kwargs

    @property
    def session(self) -> ClientSession:
        try:
            session = self._session
        except AttributeError:
            session = self._session = ClientSession(
                *self._args, connector=self._connector(), **self._kwargs
            )
            atexit.register(asyncio.run, session.close())
        return session

    @staticmethod
    def _check_response(response: ClientResponse):
        response.raise_for_status()
        if not (hist := response.history):
            return
        if (url := str(response.url)) in _warned:
            return
        warning(f'redirection from {hist[0].url} to {url}')
        _warned.add(url)

    async def get(self, *args, retry=3, **kwargs) -> ClientResponse:
        try:
            resp = await self.session.get(*args, **kwargs)
        except ServerDisconnectedError:
            if retry >= 0:
                return await self.get(*args, retry=retry - 1, **kwargs)
            raise
        self._check_response(resp)
        return resp
