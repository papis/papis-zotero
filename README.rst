ZOTERO COMPATIBILITY FOR PAPIS
==============================



Installation
------------

The general command that you have to hit is by using the ``setup.py`` script:

.. code:: python

  python3 setup.py install


Again, if you want to install it locally because you don't have administrative rights
in your computer you can just simply type

.. code:: python

  python3 setup.py install --user

If you want to develop on the code, you can also alternatively hit

.. code:: python

  python3 setup.py develop --user


.. warning::

  If you install the package locally, the program ``papis`` will be installed
  by default into your ``~/.local/bin`` direcrtory, so that you will have to
  set your ``PATH`` accordingly.

  One way of doing this in ``bash`` shells (``Linux`` and the like, also
  ``Ubuntu`` on Windows or ``cygwin``) is by adding the following line to your
  ``~/.bashrc`` file
  ::

    export PATH=$PATH:$HOME/.local/bin


