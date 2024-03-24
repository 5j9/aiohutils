from io import StringIO
from warnings import warn

from pandas import read_html
from polars import DataFrame, from_pandas


def html_to_df(html: str, index=0, /, **kwargs) -> DataFrame:
    warn('use from_html instead', DeprecationWarning)
    return read_html(StringIO(html), **kwargs)[index]


def from_html(html: str, index=0, /, **kwargs) -> DataFrame | list[DataFrame]:
    # todo: use lxml directly to avoid pandas
    rh = read_html(StringIO(html, **kwargs))
    if index is None:
        return [from_pandas(df) for df in rh]
    return from_pandas(rh[index])
