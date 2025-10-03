import os
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from papis.testing import TemporaryLibrary


@pytest.mark.skipif(os.name == "nt", reason="encoding is incorrect on windows")
@pytest.mark.library_setup(populate=False)
def test_simple(tmp_library: "TemporaryLibrary") -> None:
    from papis_zotero.bibtex import add_from_bibtex
    bibpath = os.path.join(os.path.dirname(__file__),
                           "resources", "bibtex", "zotero-library.bib")
    add_from_bibtex(bibpath, tmp_library.libname, link=False)

    from papis.database import get as get_database
    db = get_database()
    db.clear()
    db.initialize()

    from papis.id import key_name
    from papis.yaml import Loader  # type: ignore[attr-defined]

    doc, = db.query_dict({"author": "Magnus"})
    with open(doc.get_info_file(), encoding="utf-8") as fd:
        data = yaml.load(fd, Loader=Loader)
        del data[key_name()]

    info_name = os.path.join(os.path.dirname(__file__), "resources", "bibtex_out.yaml")
    with open(info_name, encoding="utf-8") as fd:
        expected_data = yaml.load(fd, Loader=Loader)

    assert data == expected_data
