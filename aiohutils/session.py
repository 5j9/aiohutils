from warnings import warn

from aiohttp import ClientResponse, ClientSession, ClientTimeout


class SessionManager:
    __slots__ = ('_session', '_args', '_kwargs')

    def __init__(
        self,
        args=(),
        kwargs={},
    ):
        self._args = args
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
        return session

    @session.setter
    def session(self, session: ClientSession):
        self._session = session

    @session.deleter
    def session(self):
        del self._session

    def _check_response(self, response: ClientResponse):
        if response.history:
            warn(f'r.history is not empty (possible redirection): {r.history}')

    async def get(self, *args, **kwargs) -> ClientResponse:
        resp = await self.session.get(*args, **kwargs)
        self._check_response(resp)
        return resp

    async def close(self):
        if (s := self.session) is not None:
            await s.close()
