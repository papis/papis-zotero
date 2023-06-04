.. image:: https://badge.fury.io/py/papis-zotero.svg
    :target: https://badge.fury.io/py/papis-zotero
.. image:: https://github.com/papis/papis-zotero/workflows/CI/badge.svg
   :target: https://github.com/papis/papis-zotero/actions?query=branch%3Amaster+workflow%3ACI

Zotero compatibility for papis
==============================

Installation
------------

To install the latest release from PyPI

.. code:: bash

    python -m pip install papis-zotero

To install the latest development version

.. code:: bash

   python -m pip install papis-zotero@https://github.com/papis/papis-zotero.git#egg=papis-zotero

Development
-----------

This project uses ``setup.py`` and ``setuptools`` for its build system.
To develop the code, it is recommended to start up a
`virtual environment <https://docs.python.org/3/library/venv.html>`__ and
install the project in editable mode using, e.g.::

    python -m pip install -e '.[develop]'

After installation always check that the command is correctly recognized, e.g.
by looking at the help output

.. code:: bash

    papis zotero --help

Importing from BibTeX
---------------------

Zotero supports exporting different variants of BibTeX or BibLaTeX files
(from ``Files > Export Library``). The resulting ``bib`` file can be directly
imported into ``papis`` using

.. code:: bash

   papis bibtex read library.bib import --all

but a better choice is using this command, as it has better support for special
Zotero fields. To import a given exported library run

.. code:: bash

    papis zotero import --from-bibtex library.bib

BibTeX files exported by Zotero can also include has some PDF entries, e.g.
they can look like

.. code:: bibtex

    @article{Einstein1905Photon,
        author = { A. Einstein },
        doi = { 10.1002/andp.19053220607 },
        journal = { Ann. Phys. },
        pages = { 132--148 },
        title = { Über einen die Erzeugung und Verwandlung des Lichtes
            betreffenden heuristischen Gesichtspunkt },
        file = { Full Text:path/to/some/relative/file.pdf },
        volume = { 322 },
        year = { 1905 },
    }

From this, ``papis-zotero`` will interpret the path of the ``file`` entry
as a relative path to ``library.bib`` passed to the import command using
``--from-bibtex``. The files are skipped if they do not exist at the expected
location.

By default, ``papis-zotero`` will add the documents to your current library.
When initially importing a big library, it is recommended to always import it
into a scratch folder, so that you can check the import. This can be easily done
using

.. code:: bash

    papis zotero import --from-bibtex library.bib --outfolder some/folder/lib

When you are ready you can move this folder to a final ``papis`` library.

Importing from Zotero SQLite
----------------------------

Zotero also maintains a database of all its files and collections under a
``zotero.sqlite`` file. You can check where this file is located by going to
``Edit > Preferences > Advanced > Data Directory Location`` (may vary depending
on the Zotero version). The Zotero data directory should contain the ``zotero.sqlite``
file and a ``storage`` directory with the files for each document.

The SQLite database maintained by Zotero can be imported directly (without
using a BibTeX export) by ``papis-zotero``. This can be done by passing

.. code:: bash

  papis zotero import --from-sql-folder <ZOTERO_DATA_DIRECTORY>

where ``ZOTERO_DATA_DIRECTORY`` is the folder containing the ``zotero.sqlite``
file. By default, ``papis-zotero`` will add the imported documents to your
current library directory, but it can be customized using the
``--outfolder`` argument.

Using Zotero connectors
-----------------------

This plugin can also connect to a Zotero connector browser plugin. First, one
such plugin should be installed from the
`Zotero website <https://www.zotero.org/download/>`__. Then, make sure that
Zotero itself is not running (and connected to the connector) and run

.. code:: bash

    papis zotero serve

to start listening to your browser for incoming data.  Whenever you click the
Zotero button to add a paper, ``papis-zotero`` will add this paper to its
library instead.
