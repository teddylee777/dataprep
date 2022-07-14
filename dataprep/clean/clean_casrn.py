"""
Clean and validate a DataFrame column containing CAS Registry Numbers.
"""
# pylint: disable=too-many-lines, too-many-arguments, too-many-branches, unused-argument
from typing import Any, Union
from operator import itemgetter

import dask.dataframe as dd
import numpy as np
import pandas as pd

from stdnum import casrn
from ..progress_bar import ProgressBar
from .utils import NULL_VALUES, to_dask


def clean_casrn(
    df: Union[pd.DataFrame, dd.DataFrame],
    column: str,
    output_format: str = "standard",
    split: bool = False,
    inplace: bool = False,
    errors: str = "coerce",
    progress: bool = True,
) -> pd.DataFrame:
    """
    Clean CAS Registry Numbers type data in a DataFrame column.

    Parameters
    ----------
        df
            A pandas or Dask DataFrame containing the data to be cleaned.
        column
            The name of the column containing data of ISBN type.
        output_format
            The output format of standardized number string.
            If output_format = 'compact', return string without any separators.
            If output_format = 'standard', return string with proper separators.

            (default: "standard")
        split
            If True,
                each component of derived from its number string will be put into its own column.

            (default: False)
        inplace
           If True, delete the column containing the data that was cleaned.
           Otherwise, keep the original column.

           (default: False)
        errors
            How to handle parsing errors.
            - ‘coerce’: invalid parsing will be set to NaN.
            - ‘ignore’: invalid parsing will return the input.
            - ‘raise’: invalid parsing will raise an exception.

            (default: 'coerce')
        progress
            If True, display a progress bar.

            (default: True)

    Examples
    --------
    Clean a column of CAS Registry Numbers data.

    >>> df = pd.DataFrame({
            "casrn": [
            "87-86-5"]
            })
    >>> clean_casrn(df, 'casrn', inplace=True)
           casrn_clean
    0      87865
    """

    if output_format not in {"compact", "standard"}:
        raise ValueError(
            f"output_format {output_format} is invalid. " 'It needs to be "compact", "standard".'
        )

    # convert to dask
    df = to_dask(df)

    # To clean, create a new column "clean_code_tup" which contains
    # the cleaned values and code indicating how the initial value was
    # changed in a tuple. Then split the column of tuples and count the
    # amount of different codes to produce the report
    df["clean_code_tup"] = df[column].map_partitions(
        lambda srs: [_format(x, output_format, split, errors) for x in srs],
        meta=object,
    )

    df = df.assign(
        _temp_=df["clean_code_tup"].map(itemgetter(0)),
    )

    df = df.rename(columns={"_temp_": f"{column}_clean"})

    df = df.drop(columns=["clean_code_tup"])

    if inplace:
        df[column] = df[f"{column}_clean"]
        df = df.drop(columns=f"{column}_clean")
        df = df.rename(columns={column: f"{column}_clean"})

    with ProgressBar(minimum=1, disable=not progress):
        df = df.compute()

    # output a report describing the result of clean_country
    return df


def validate_casrn(
    df: Union[str, pd.Series, dd.Series, pd.DataFrame, dd.DataFrame],
    column: str = "",
) -> Union[bool, pd.Series, pd.DataFrame]:
    """
    Validate if a data cell is CAS Registry Numbers in a DataFrame column.
    For each cell, return True or False.

    Parameters
    ----------
    df
            A pandas or Dask DataFrame containing the data to be validated.
    column
            The name of the column to be validated.
    """
    if isinstance(df, (pd.Series, dd.Series)):
        return df.apply(casrn.is_valid)
    elif isinstance(df, (pd.DataFrame, dd.DataFrame)):
        if column != "":
            return df[column].apply(casrn.is_valid)
        else:
            return df.applymap(casrn.is_valid)
    return casrn.is_valid(df)


def _format(
    val: Any, output_format: str = "standard", split: bool = False, errors: str = "coarse"
) -> Any:
    """
    Reformat a number string with proper separators (formats).

    Parameters
    ----------
    val
           The value of number string.
    output_format
           If output_format = 'compact', return string without any separators.
           If output_format = 'standard', return string with proper separators function.
    """
    val = str(val)
    result: Any = []

    if val in NULL_VALUES:
        return [np.nan]

    if not validate_casrn(val):
        if errors == "raise":
            raise ValueError(f"Unable to parse value {val}")
        error_result = val if errors == "ignore" else np.nan
        return [error_result]

    result = [casrn.compact(val)] + result

    return result