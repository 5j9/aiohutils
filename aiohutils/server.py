from pathlib import Path
from warnings import warn
from zlib import adler32

from aiohttp.web import Application, FileResponse, Request, RouteDef, get


def static_path(file: Path) -> tuple[str, RouteDef]:
    warn(
        'aiohutils.static_path is deprecated; use aiohutils.serve_static instead.',
        DeprecationWarning,
        stacklevel=2,
    )
    serve_path = (
        f'/static/{adler32(str(file.absolute()).encode())}/{file.name}'
    )

    async def handler(_: Request) -> FileResponse:
        return FileResponse(
            file, headers={'Cache-Control': 'immutable,   max-age=604800'}
        )

    return serve_path, get(serve_path, handler)


def serve_static(app: Application, file: Path) -> None:
    async def handler(_: Request) -> FileResponse:
        return FileResponse(
            file, headers={'Cache-Control': 'immutable,   max-age=604800'}
        )

    app.router.add_get(f'/static/{file.name}', handler)
