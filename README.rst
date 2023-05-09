.. image:: https://badge.fury.io/py/papis-zotero.svg
    :target: https://badge.fury.io/py/papis-zotero

|ghbadge|

ZOTERO COMPATIBILITY FOR PAPIS
==============================


Importing using bibtex files
----------------------------

After installation check always the help options

Now the zotero script is accessible from papis:

.. code:: bash

  papis zotero -h

If you have a bibtex somewhere in your computer, you can use the script:

.. code:: bash

  papis zotero import --from-bibtex library.bib

.. warning::

  Note that if your bibtex file has some pdf entries, i.e., it looks like:

  .. code:: bibtex

    @article{Einstein1905Photon,
      author = { A. Einstein },
      doi = { 10.1002/andp.19053220607 },
      journal = { Ann. Phys. },
      pages = { 132--148 },
      title = { Über einen die Erzeugung und Verwandlung des Lichtes betreffenden heuristischen Gesichtspunkt },
      FILE = { path/to/some/relative/file.pdf },
      volume = { 322 },
      year = { 1905 },
    }

  then ``papis-zotero`` will interpret the path of the ``FILE`` entry
  as a relative path, so you should run the command from where this relative path
  makes sense.

Importing using zotero sql files
--------------------------------

There is also a script that decodes the
``zotero.sqlite`` sqlite file that ``zotero`` uses to manage documents
and creates papis Documents out of it.

This script will retrieve the documents from zotero (be it ``pdf`` documents
or something else) and important information like tags.

Now you have to go to the directory where zotero saves all the information,
it would look something like this on linux systems:

.. code:: bash

  cd ~/.mozilla/firefox/zqb7ju1q.default/zotero

Maybe the path is slightly different. It may vary from version to version from
zotero.  In the zotero data directory there should be a file called
``zotero.sqlite`` and there might be a ``storage`` directory with
document data inside. These will be used by ``zotero-sql`` to
retrieve information and files from.

Now you can use the script through

.. code:: bash

  papis zotero import --from-sql-folder YOUR-SQL-FOLDER

where ``YOUR-SQL-FOLDER`` is the folder containing the ``zotero.sqlite``
folder.

This script by default will create a directory named ``Documents`` (in your
current directory) where papis documents are stored. You can add these document
by simply moving them to your library folder

.. code::

  mv Documents/*      /path/to/your/papis/library

or also by adding them through papis using the folder flag

.. code::

  papis add --from-folder Documents/ZOTERO_ID

or write a ``bash`` for-loop to do it with all the converted documents

.. code::

  for folder in Documents/* ; do papis add --from-folder $folder ; done

.. warning::

   When importing, I recommend always import the library into a scatch folder,
   so that you can make tests, this would look lik

   .. code:: bash
    
      papis zotero import --from-sql YOUR-SQL-FILE --outfolder TEST_FOLDER

   When you are ready you can move this folder into your papis library yourself.



Use zotero conectors
--------------------

Just install the zotero connector browser plugin
`here <https://www.zotero.org/download/>`_
and type

::

  papis zotero serve

to start listening to your browser for incoming data.  Whenever you click the
zotero button to add a paper, papis will add this paper to the library.


Installation from pypi
----------------------

Just run

::

  sudo pip3 install papis-zotero

Installation
------------

The general command that you have to hit is by using the ``setup.py`` script:

::

  python3 setup.py install


Again, if you want to install it locally because you don't have administrative rights
in your computer you can just simply type

::

  python3 setup.py install --user

If you want to develop on the code, you can also alternatively hit

::

  python3 setup.py develop --user

.. |ghbadge| image:: https://github.com/papis/papis-zotero/workflows/CI/badge.svg
