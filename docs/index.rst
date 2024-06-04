.. awpy documentation master file, created by
   sphinx-quickstart on Sun Jan 30 21:22:52 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

awpy
===================
|Discord| |Github| |Build| |Licence|

.. |Discord| image:: https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord
   :target: https://discord.gg/W34XjsSs2H
   
.. |Github| image:: https://img.shields.io/badge/github-repo-yellowgreen
   :target: https://github.com/pnxenopoulos/awpy
   
.. |Build| image:: https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg
   :target: https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml
   
.. |License| image:: https://img.shields.io/badge/license-MIT-lightgrey
   :target: https://github.com/pnxenopoulos/awpy/blob/main/LICENSE
   
`awpy` allows a user to parse, analyze and visualize Counter-Strike 2 demo files. You can visit the repository_ to view the source code, examples and data. Please join the Discord_ server if you would like to join our esports analytics community or to receive help. To install the library, run ``pip install awpy`` (Python >= 3.9).

.. _repository: https://github.com/pnxenopoulos/awpy
.. _Discord: https://discord.gg/W34XjsSs2H

Using Awpy to parse Counter-Strike 2 demos is as easy as the few lines of code shown below. To see what output looks like, check out :doc:`parser_output`.

.. code-block:: python

   from awpy import Demo

   # Simply call `Demo(path="...")` to parse a demo
   dem = Demo("natus-vincere-vs-virtus-pro-m1-overpass.dem")

   # Access various dictionaries & dataframes
   dem.header
   dem.rounds
   dem.grenades
   dem.kills
   dem.damages
   dem.bomb
   dem.smokes
   dem.infernos
   dem.weapon_fires
   dem.ticks


Using Awpy
----------
:doc:`installation`
   How to install `awpy`.

:doc:`examples`
   Examples code and Jupyter notebooks to help get you started.

:doc:`faq`
   Need help? Check the FAQs first.

:doc:`license`
   License and acknowledgments.

awpy Modules
------------
:doc:`data`
   Data module.

:doc:`parsing`
   Parsing modules.

:doc:`stats`
   Stats module.

:doc:`vis`
   Visualization module.

.. Hidden TOCs

.. toctree::
   :caption: Getting Started
   :maxdepth: 2
   :hidden:

   installation
   examples
   projects
   faq
   license

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   data
   parser
   stats
   visualization
