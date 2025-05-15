import atexit
from collections.abc import Iterator, Mapping
from inspect import iscoroutinefunction
from itertools import cycle
from typing import NotRequired, TypedDict, get_args, get_origin, is_typeddict
from unittest.mock import patch

from decouple import config
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
    print('inside session fixture')
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


def assert_dict_type(dct: Mapping, typed_dct: type[TypedDict]):  # type: ignore
    not_required = dct.keys() - typed_dct.__required_keys__
    assert typed_dct.__optional_keys__ >= not_required, (
        'the following keys are neither required nor optional:\n'
        f'{not_required - typed_dct.__optional_keys__}'
    )
    annotations = typed_dct.__annotations__
    for k, v in dct.items():
        expected_type = annotations[k]
        if is_typeddict(expected_type):
            assert_dict_type(v, expected_type)
            continue
        if get_origin(expected_type) is NotRequired:
            expected_type = get_args(expected_type)
        assert isinstance(v, expected_type), f'{k=} {v=} {expected_type=}'
