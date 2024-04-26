from pathlib import Path
from zlib import adler32

from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_routedef import RouteDef, get


def static_path(file: Path) -> tuple[str, RouteDef]:
    get_path = f'/static/{adler32(str(file.absolute()).encode())}/{file.name}'

    async def handler(_: Request) -> FileResponse:
        return FileResponse(
            file, headers={'Cache-Control': 'immutable,   max-age=604800'}
        )

    return get_path, get(get_path, handler)
