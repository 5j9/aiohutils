import asyncio
import atexit
from warnings import warn

from aiohttp import ClientResponse, ClientSession, ClientTimeout


class SessionManager:
    __slots__ = ('_session', '_args', '_kwargs')

    def __init__(
        self,
        args=(),
        kwargs=None,
    ):
        self._args = args

        if kwargs is None:
            kwargs = {}
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
                *self._args, **self._kwargs
            )
            atexit.register(asyncio.run, session.close())
        return session

    @staticmethod
    def _check_response(response: ClientResponse):
        if response.history:
            warn(
                f'r.history is not empty (possible redirection): {response.history}'
            )

    async def get(self, *args, **kwargs) -> ClientResponse:
        resp = await self.session.get(*args, **kwargs)
        self._check_response(resp)
        return resp
