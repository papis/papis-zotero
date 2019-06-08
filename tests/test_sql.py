import papis_zotero.sql
import os
import glob
import tempfile

def test_simple():
    sqlpath = os.path.join(os.path.dirname(__file__), 'data', 'Zotero')
    libdir = tempfile.mkdtemp()
    papis_zotero.sql.add_from_sql(sqlpath, libdir)
    folders = os.listdir(libdir)
    assert(len(folders) == 19)
    assert(len(glob.glob(libdir + "/**/*.pdf")) == 5)
