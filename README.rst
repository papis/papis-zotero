.. image:: https://badge.fury.io/py/papis-zotero.svg
    :target: https://badge.fury.io/py/papis-zotero

.. image:: https://travis-ci.org/papis/papis-zotero.svg?branch=master
    :target: https://travis-ci.org/papis/papis-zotero

ZOTERO COMPATIBILITY FOR PAPIS
==============================


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
