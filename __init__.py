from asyncio import new_event_loop
from unittest.mock import patch
from os import getenv

from pytest import fixture
from dotenv import load_dotenv


# https://stackoverflow.com/a/71133268/2705757
def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


load_dotenv()
RECORD_MODE = strtobool(getenv('RECORD_MODE'))
OFFLINE_MODE = strtobool(getenv('OFFLINE_MODE')) and not RECORD_MODE


class FakeResponse:

    file = ''

    async def read(self):
        with open(self.file, 'rb') as f:
            content = f.read()
        return content


def session_fixture_factory(main_module):

    @fixture(scope='session', autouse=True)
    async def session():
        if OFFLINE_MODE:

            class FakeSession:
                @staticmethod
                async def get(_):
                    return FakeResponse()

            main_module.SESSION = FakeSession()
            yield
            return

        session = main_module.Session()

        if RECORD_MODE:
            original_get = session.get

            async def recording_get(*args, **kwargs):
                resp = await original_get(*args, **kwargs)
                content = await resp.read()
                with open(FakeResponse.file, 'wb') as f:
                    f.write(content)
                return resp

            session.get = recording_get

        yield
        await session.close()

    return session


@fixture(scope='session')
def event_loop():
    loop = new_event_loop()
    yield loop
    loop.close()


def file(filename):
    return patch.object(FakeResponse, 'file', f'{__file__}/../../testdata/{filename}')
