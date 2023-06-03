import os
import glob
import tempfile

import papis.logging
import papis_zotero.sql

papis.logging.setup()


def test_simple() -> None:
    with tempfile.TemporaryDirectory() as libdir:
        sqlpath = os.path.join(os.path.dirname(__file__), "data", "Zotero")
        papis_zotero.sql.add_from_sql(sqlpath, libdir)

        folders = os.listdir(libdir)
        assert len(folders) == 5
        assert len(glob.glob(libdir + "/**/*.pdf")) == 4

        doc = papis.document.from_folder(os.path.join(libdir, folders[0]))
        assert doc.get_files()
        assert doc["ref"] in folders
