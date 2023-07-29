.. seedr-client documentation master file, created by
   sphinx-quickstart on Thu Jul 27 12:26:02 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to SeedrClient's documentation!
========================================


Content
-------

.. toctree::
   :maxdepth: 3

   Project Homepage <https://github.com/Mr-Developer-X/SeedrClient>
   modules



Example Usage
-------------

.. code-block:: python

   from seedr_client import SeedrHandler


   seedr = SeedrHandler(email="youremail@example.com", password="your_password")
   print(seedr.get_drive())
   # Should return a similar result
   # {'space': {'total': '5.0 GB', 'used': '1.1 GB'}, 'parent_folder_id': 123456789,
   # 'torrents': [], 'folders': [{'folder_id': 123456799, 'folder_name':
   # 'Ubuntu Minimal ISO 22.04 Custom', 'size': '1.1 GB'}], 'files': []}


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. role:: raw-html(raw)
    :format: html

:raw-html:`<br />`


.. note::

   This is an automatically generated documentation and therefore certain details may not be explained with
   great precision. If you have issues with the documentation or understanding any of the methods, you can raise an Github
   issues and I will try to help you regarding those.


