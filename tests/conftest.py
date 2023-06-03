##
# This is copied from `papis/tests/conftest.py` and should be kept in sync as
# much as possible until we clean it up and can depend on newer versions of papis
##

import pytest
from typing import Iterator

from tests import testlib


@pytest.fixture()
def tmp_config(
        request: pytest.FixtureRequest
        ) -> Iterator[testlib.TemporaryConfiguration]:
    marker = request.node.get_closest_marker("config_setup")
    kwargs = marker.kwargs if marker else {}

    with testlib.TemporaryConfiguration(**kwargs) as config:
        yield config


@pytest.fixture()
def tmp_library(
        request: pytest.FixtureRequest
        ) -> Iterator[testlib.TemporaryLibrary]:
    marker = request.node.get_closest_marker("library_setup")
    kwargs = marker.kwargs if marker else {}

    with testlib.TemporaryLibrary(**kwargs) as lib:
        yield lib
