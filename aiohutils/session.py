import asyncio
import atexit
from collections.abc import Callable
from logging import warning
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

_warned = set()


class SessionManager:
    __slots__ = ('_args', '_connector', '_kwargs', '_session')

    def __init__(
        self,
        *args,
        connector: Callable[[], TCPConnector | None] = lambda: TCPConnector(
            resolver=ThreadedResolver()
        ),
        **kwargs,
    ):
        self._args = args
        self._connector = connector

        self._kwargs = {
            'timeout': ClientTimeout(
                total=30.0, sock_connect=15.0, sock_read=15.0
            ),
        } | kwargs

    @property
    def session(self) -> ClientSession:
        try:
            return self._session
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
