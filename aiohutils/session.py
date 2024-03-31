import asyncio
import atexit
from collections.abc import Callable
from logging import info
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

    async def get(self, *args, **kwargs) -> ClientResponse:
        try:
            resp = await self.session.get(*args, **kwargs)
        except ServerDisconnectedError:
            info('ServerDisconnectedError; will retry instantly')
            return await self.get(*args, **kwargs)
        self._check_response(resp)
        return resp
