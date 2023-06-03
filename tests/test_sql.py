import os
import glob
import yaml
import pytest

import papis.yaml
import papis.document
import papis_zotero.sql

from .testlib import TemporaryLibrary


@pytest.mark.library_setup(populate=False)
def test_simple(tmp_library: TemporaryLibrary) -> None:
    sqlpath = os.path.join(os.path.dirname(__file__), "resources", "sql")
    papis_zotero.sql.add_from_sql(sqlpath)

    folders = os.listdir(tmp_library.libdir)
    assert len(folders) == 5
    assert len(glob.glob(tmp_library.libdir + "/**/*.pdf")) == 4

    doc = papis.document.from_folder(os.path.join(tmp_library.libdir, "IH8J2JJP"))

    info_name = os.path.join(os.path.dirname(__file__), "resources", "sql_out.yaml")
    with open(info_name, encoding="utf-8") as fd:
        data = yaml.load(fd, Loader=papis.yaml.Loader)  # type: ignore[attr-defined]
        expected_doc = papis.document.from_data(data)

    assert expected_doc["ref"] == doc["ref"]

    # FIXME: currently fails on windows
    # assert doc.get_files()
