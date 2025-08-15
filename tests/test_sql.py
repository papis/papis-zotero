import glob
import os

import pytest
import yaml

import papis.document
import papis.yaml
from papis.testing import TemporaryLibrary

import papis_zotero.sql


@pytest.mark.skipif(os.name == "nt", reason="encoding is incorrect on windows")
@pytest.mark.library_setup(populate=False)
def test_simple(tmp_library: TemporaryLibrary) -> None:
    sqlpath = os.path.join(os.path.dirname(__file__), "resources", "sql")
    papis.config.set("add-folder-name", "{doc[author]}")
    papis_zotero.sql.add_from_sql(sqlpath)

    folders = os.listdir(tmp_library.libdir)
    assert len(folders) == 5
    assert len(glob.glob(tmp_library.libdir + "/**/*.pdf")) == 4

    doc = papis.document.from_folder(
        os.path.join(
            tmp_library.libdir,
            "svard-magnus-and-nordstrom-jan"
            )
        )

    info_name = os.path.join(os.path.dirname(__file__), "resources", "sql_out.yaml")
    with open(info_name, encoding="utf-8") as fd:
        data = yaml.load(fd, Loader=papis.yaml.Loader)  # type: ignore[attr-defined]
        expected_doc = papis.document.from_data(data)

    assert expected_doc["author"] == doc["author"]

    # FIXME: currently fails on windows
    # assert doc.get_files()
