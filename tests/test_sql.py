import os
import glob
import pytest

import papis.document
import papis_zotero.sql

@pytest.mark.library_setup(populate=False)
def test_simple(tmp_library: TemporaryLibrary) -> None:
    sqlpath = os.path.join(os.path.dirname(__file__), "data", "Zotero")
    papis_zotero.sql.add_from_sql(sqlpath, tmp_library.libdir)
    folders = os.listdir(tmp_library.libdir)
    assert len(folders) == 5
    assert len(glob.glob(tmp_library.libdir + "/**/*.pdf")) == 4

    doc = papis.document.from_folder(os.path.join(tmp_library.libdir, folders[0]))
    assert doc["ref"] in folders

    # FIXME: currently fails on windows
    # assert doc.get_files()
