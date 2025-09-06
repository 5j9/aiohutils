import atexit
from collections.abc import Iterator, Mapping
from inspect import iscoroutinefunction
from itertools import cycle
from typing import TypedDict
from unittest.mock import patch
from warnings import deprecated

from decouple import config
from pydantic import ConfigDict
from pydantic.type_adapter import TypeAdapter
from pytest import Function, fixture

from aiohutils.session import ClientSession, SessionManager

RECORD_MODE: bool = False
OFFLINE_MODE: bool = True
TESTS_PATH: str
REMOVE_UNUSED_TESTDATA: bool = False


def init_tests():
    global RECORD_MODE, OFFLINE_MODE, TESTS_PATH, REMOVE_UNUSED_TESTDATA

    config.search_path = TESTS_PATH = config._caller_path()  # type: ignore

    RECORD_MODE = config('RECORD_MODE', False, cast=bool)  # type: ignore
    OFFLINE_MODE = config('OFFLINE_MODE', True, cast=bool) and not RECORD_MODE  # type: ignore
    REMOVE_UNUSED_TESTDATA = (  # type: ignore
        config('REMOVE_UNUSED_TESTDATA', False, cast=bool) and OFFLINE_MODE
    )


class EqualToEverything:
    def __eq__(self, other):
        return True


class FakeResponse:
    __slots__ = 'files'
    files: Iterator
    url = EqualToEverything()
    history = ()

    @property
    def file(self) -> str:
        return next(self.files)

    async def read(self) -> bytes:
        with open(self.file, 'rb') as f:
            return f.read()

    def raise_for_status(self):
        pass

    async def text(self) -> str:
        return (await self.read()).decode()


@fixture(scope='session')
async def session():
    if OFFLINE_MODE:

        class FakeSession:
            @staticmethod
            async def get(*_, **__):
                return FakeResponse()

        orig_session = SessionManager.session
        SessionManager.session = FakeSession()  # type: ignore
        yield
        SessionManager.session = orig_session  # type: ignore
        return

    if RECORD_MODE:
        original_get = ClientSession.get

        async def recording_get(*args, **kwargs):
            resp = await original_get(*args, **kwargs)
            content = await resp.read()
            with open(FakeResponse().file, 'wb') as f:
                f.write(content)
            return resp

        ClientSession.get = recording_get  # type: ignore

        yield
        ClientSession.get = original_get
        return

    yield
    return


def pytest_collection_modifyitems(items: list[Function]):
    for item in items:
        if iscoroutinefunction(item.obj):
            item.fixturenames.append('session')


def remove_unused_testdata():
    if REMOVE_UNUSED_TESTDATA is not True:
        return
    import os

    unused_testdata = (
        set(os.listdir(f'{TESTS_PATH}/testdata/')) - USED_FILENAMES
    )
    if not unused_testdata:
        print('REMOVE_UNUSED_TESTDATA: no action required')
        return
    for filename in unused_testdata:
        os.remove(f'{TESTS_PATH}/testdata/{filename}')
        print(f'REMOVE_UNUSED_TESTDATA: removed {filename}')


USED_FILENAMES = set()
atexit.register(remove_unused_testdata)


def file(filename: str):
    if REMOVE_UNUSED_TESTDATA is True:
        USED_FILENAMES.add(filename)
    return patch.object(
        FakeResponse,
        'files',
        cycle([f'{TESTS_PATH}/testdata/{filename}']),
    )


def files(*filenames: str):
    if REMOVE_UNUSED_TESTDATA is True:
        for filename in filenames:
            USED_FILENAMES.add(filename)
    return patch.object(
        FakeResponse,
        'files',
        (f'{TESTS_PATH}/testdata/{filename}' for filename in filenames),
    )


strict_config = ConfigDict(strict=True)


def validate_typed_dict(dct: Mapping, typed_dct: type[TypedDict]):  # type: ignore
    # A trick to disallow extra keys. See
    # https://stackoverflow.com/questions/77165374/runtime-checking-for-extra-keys-in-typeddict
    # https://docs.pydantic.dev/2.4/concepts/strict_mode/#dataclasses-and-typeddict
    typed_dct.__pydantic_config__ = strict_config  # type: ignore
    TypeAdapter(typed_dct).validate_python(dct, strict=True)


@deprecated('assert_dict_type is deprecated in favour of validate_typed_dict')
def assert_dict_type(dct: Mapping, typed_dct: type[TypedDict]):  # type: ignore
    validate_typed_dict(dct, typed_dct)
