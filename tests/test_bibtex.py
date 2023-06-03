import os
import yaml
import pytest

import papis.id
import papis.yaml
import papis.database
import papis.document
import papis_zotero.bibtex

from .testlib import TemporaryLibrary


@pytest.mark.skipif(os.name == "nt", reason="encoding is incorrect on windows")
@pytest.mark.library_setup(populate=False)
def test_simple(tmp_library: TemporaryLibrary) -> None:
    bibpath = os.path.join(os.path.dirname(__file__),
                           "resources", "bibtex", "zotero-library.bib")
    papis_zotero.bibtex.add_from_bibtex(bibpath, tmp_library.libname, link=False)

    db = papis.database.get()
    db.clear()
    db.initialize()

    doc, = db.query_dict({"author": "Magnus"})
    with open(doc.get_info_file(), encoding="utf-8") as fd:
        data = yaml.load(
            fd, Loader=papis.yaml.Loader)  # type: ignore[attr-defined]
        del data[papis.id.key_name()]

    info_name = os.path.join(os.path.dirname(__file__), "resources", "bibtex_out.yaml")
    with open(info_name, encoding="utf-8") as fd:
        expected_data = yaml.load(
            fd, Loader=papis.yaml.Loader)  # type: ignore[attr-defined]

    assert data == expected_data
