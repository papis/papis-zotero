.. image:: https://badge.fury.io/py/papis-zotero.svg
    :target: https://badge.fury.io/py/papis-zotero
.. image:: https://github.com/papis/papis-zotero/workflows/CI/badge.svg
   :target: https://github.com/papis/papis-zotero/actions?query=branch%3Amaster+workflow%3ACI

ZOTERO COMPATIBILITY FOR PAPIS
==============================

Installation from source
------------------------

This project uses ``setup.py`` and ``setuptools`` for its build system. It can
be installed (system-wide or per-user) with::

    python setup.py install
    python setup.py install --user

To develop the code, it is recommended to start up a virtual environment and
install the project in editable mode using, e.g.::

    python -m pip install -e '.[develop]'

After installation always check that the command is correctly recognized, e.g.
by looking at the help output

.. code:: bash

    papis zotero --help

Installation from PyPI
----------------------

.. code:: bash

    python -m pip install papis-zotero

Importing using BibTeX files
----------------------------

Zotero supports exporting different variants of BibTeX or BibLaTeX files.
These can be directly imported into ``papis`` using

.. code:: bash

   papis bibtex read library.bib import --all

but a better choice is using this command, as it has better support for special
Zotero fields. The files can be imported with

.. code:: bash

    papis zotero import --from-bibtex library.bib

Note that if your BibTeX file has some PDF entries, i.e. it looks like:

.. code:: bibtex

    @article{Einstein1905Photon,
        author = { A. Einstein },
        doi = { 10.1002/andp.19053220607 },
        journal = { Ann. Phys. },
        pages = { 132--148 },
        title = { Über einen die Erzeugung und Verwandlung des Lichtes
            betreffenden heuristischen Gesichtspunkt },
        FILE = { path/to/some/relative/file.pdf },
        volume = { 322 },
        year = { 1905 },
    }

then ``papis-zotero`` will interpret the path of the ``FILE`` entry
as a relative path, so you should run the command from where this relative path
makes sense.

Importing using Zotero SQLite files
-----------------------------------

There is also a script that decodes the ``zotero.sqlite`` file that Zotero
uses to manage documents and creates papis documents out of it.

This script will retrieve the documents from Zotero (be it ``pdf`` documents
or something else) and important information (e.g. tags).

Now you have to go to the directory where Zotero saves all the information,
it would look something like this on linux systems:

.. code:: bash

    cd ~/.mozilla/firefox/zqb7ju1q.default/zotero

Maybe the path is slightly different. It may vary from version to version from
Zotero.  In the Zotero data directory there should be a file called
``zotero.sqlite`` and there might be a ``storage`` directory with
document data inside. These will be used by ``zotero-sql`` to
retrieve information and files from.

Now you can use the script through

.. code:: bash

  papis zotero import --from-sql-folder YOUR-SQL-FOLDER

where ``YOUR-SQL-FOLDER`` is the folder containing the ``zotero.sqlite``
folder.

This script by default will create a directory named ``Documents`` (in your
current directory) where ``papis`` documents are stored. You can add these
documents by simply moving them to your library folder

.. code::

    mv Documents/* /path/to/your/papis/library

or by adding them through ``papis`` using the folder flag

.. code::

    papis add --from-folder Documents/ZOTERO_ID

or write a ``bash`` for-loop to do it with all the converted documents

.. code::

    for folder in Documents/*; do papis add --from-folder "$folder"; done

When importing, it is recommended to always import the library into a scatch
folder, so that you can check the import. This can be easily done using

.. code:: bash

    papis zotero import --from-sql YOUR-SQL-FILE --outfolder TEST_FOLDER

When you are ready you can move this folder to a final ``papis`` library.

Using Zotero connectors
-----------------------

Just install the Zotero connector browser plugin from
`here <https://www.zotero.org/download/>`__ and type::

    papis zotero serve

to start listening to your browser for incoming data.  Whenever you click the
Zotero button to add a paper, papis will add this paper to its library.
