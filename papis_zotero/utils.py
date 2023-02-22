import os
import re
from typing import Iterable


def is_pdf(filepath: str) -> bool:
    if not os.path.exists(filepath):
        return False

    with open(filepath, "rb") as fd:
        magic = fd.read(8)

    return re.match(r"%PDF-.\..", magic.decode()) is not None


def to_sql_tuple(elements: Iterable[str]) -> str:
    """Concatenate given strings to SQL tuple of strings."""

    elements_tuple = "("
    for element in elements:
        if elements_tuple != "(":
            elements_tuple += ","
        elements_tuple += '"' + element + '"'
    elements_tuple += ")"

    return elements_tuple
