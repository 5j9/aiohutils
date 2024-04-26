from io import StringIO
from warnings import warn

from pandas import read_html
from polars import DataFrame, from_pandas

warn('aiohutils.df will be deprecated', PendingDeprecationWarning, 2)


def from_html(html: str, index=0, /, **kwargs) -> DataFrame | list[DataFrame]:
    # todo: use lxml directly to avoid pandas
    rh = read_html(StringIO(html), **kwargs)
    if index is None:
        return [from_pandas(df) for df in rh]
    return from_pandas(rh[index])
