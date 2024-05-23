|pypi| |ci|

Zotero compatibility for Papis
==============================

Installation
------------

Pip
^^^

To install the latest release from PyPI

.. code:: bash

    python -m pip install papis-zotero

To install the latest development version

.. code:: bash

    python -m pip install papis-zotero@https://github.com/papis/papis-zotero.git#egg=papis-zotero

Nix
^^^

For Nix and NixOS users, a Nix flake is included in this repository and can be
used to install the package. There are many ways of doing so, for instance like so:

.. code:: nix

    {
      pkgs,
      inputs,
      ...
    }: {
      home.packages = with pkgs; [
        (
          python3.withPackages
          (
            ps: [
              inputs.papis.packages.${system}.default
              inputs.papis-zotero.packages.${system}.default
              # you can add other packages you might want to make available for papis
              # ps.jinja2
            ]
          )
        )
        # Here you can list other packages, such as
        # typst
        # hayagriva
        # zotero_7
      ];
    }

Arch
^^^^

Arch users can use the AUR to install `the package
<https://aur.archlinux.org/packages/papis-zotero>`__.

Importing from Zotero SQLite (preferred)
----------------------------------------

Zotero also maintains a database of all its files and collections under a
``zotero.sqlite`` file. You can check where this file is located by going to
``Edit > Preferences > Advanced > Data Directory Location`` (may vary depending
on the Zotero version). The Zotero data directory should contain the ``zotero.sqlite``
file and a ``storage`` directory with the files for each document.

The SQLite database maintained by Zotero can be imported directly (without
using a BibTeX export) by ``papis-zotero``. This can be done with:

.. code:: bash

  papis zotero import --from-sql-folder <ZOTERO_DATA_DIRECTORY>

Here, ``ZOTERO_DATA_DIRECTORY`` is the folder containing the ``zotero.sqlite``
file. By default, ``papis-zotero`` will add the imported documents to your
current library directory, but it can be customized using the
``--outfolder`` argument.

Importing from BibTeX (alternative)
-----------------------------------

Zotero can export different variants of BibTeX or BibLaTeX files
(from ``Files > Export Library``). You could import the resulting ``.bib`` file
directly with Papis (with the ``papis bibtex`` command), but ``papis-zotero``
provides a specialised command. This command has better support for special Zotero
fields. To import a given exported library run:

.. code:: bash

    papis zotero import --from-bibtex library.bib

BibTeX files exported by Zotero can include attached files as shown in the below
example:

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

Given this, ``papis-zotero`` will interpret the path of the ``file`` entry
as a relative path to the ``library.bib`` passed to the import command using
``--from-bibtex``. The files are skipped if they do not exist at the expected
location.

By default, ``papis-zotero`` will add the documents to your current library.
When initially importing a big library, it is recommended to always import it
into a scratch folder, so that you can verify the import. This can be easily done
using:

.. code:: bash

    papis zotero import --from-bibtex library.bib --outfolder some/folder/lib

When you are ready you can move this folder to a final Papis library.

Using Zotero connectors
-----------------------

This plugin can also connect to a Zotero connector browser plugin. First, such
a plugin should be installed from the
`Zotero website <https://www.zotero.org/download/>`__. Then, make sure that
Zotero itself is not running (and connected to the connector) and run:

.. code:: bash

    papis zotero serve

Papis now starts listening to your browser for incoming data. Whenever you click the
Zotero button to add a paper, ``papis-zotero`` will add this paper to the Papis
library instead.

Development
-----------

This project uses ``pyproject.toml`` and ``hatchling`` for its build system.
To develop the code, it is recommended to start up a
`virtual environment <https://docs.python.org/3/library/venv.html>`__ and
install the project in editable mode using, e.g.::

    python -m pip install -e '.[develop]'

After installation, always check that the command is correctly recognized, e.g.
by looking at the help output

.. code:: bash

    papis zotero --help

If you use the Nix flake, you can also use the included ``devShell`` with
``nix develop``.


.. |pypi| image:: https://badge.fury.io/py/papis-zotero.svg
   :target: https://badge.fury.io/py/papis-zotero
.. |ci| image:: https://github.com/papis/papis-zotero/workflows/CI/badge.svg
   :target: https://github.com/papis/papis-zotero/actions?query=branch%3Amain+workflow%3ACI
