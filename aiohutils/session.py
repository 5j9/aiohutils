import asyncio
import atexit
from collections.abc import Callable
from warnings import warn

from aiohttp import (
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ServerDisconnectedError,
    TCPConnector,
)


class SessionManager:
    __slots__ = ('_session', '_args', '_kwargs', '_connector')

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
        if response.history:
            warn(
                f'redirection from {response.history[0].url} to {response.url}'
            )

    async def get(self, *args, retry=3, **kwargs) -> ClientResponse:
        try:
            resp = await self.session.get(*args, **kwargs)
        except ServerDisconnectedError:
            if retry >= 0:
                return await self.get(*args, retry=retry - 1, **kwargs)
            raise
        self._check_response(resp)
        return resp
