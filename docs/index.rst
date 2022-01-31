.. csgo documentation master file, created by
   sphinx-quickstart on Sun Jan 30 21:22:52 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

csgo Python Library
===================
|Discord| |Github| |Build| |Licence|

.. |Discord| image:: https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord
   :target: https://discord.gg/W34XjsSs2H
   
.. |Github| image:: https://img.shields.io/badge/github-repo-yellowgreen
   :target: https://github.com/pnxenopoulos/csgo
   
.. |Build| image:: https://github.com/pnxenopoulos/csgo/actions/workflows/build.yml/badge.svg
   :target: https://github.com/pnxenopoulos/csgo/actions/workflows/build.yml
   
.. |Licence| image:: https://img.shields.io/badge/license-MIT-lightgrey
   :target: https://github.com/pnxenopoulos/csgo/blob/main/LICENSE
   
This Python library allows a user to parse, analyze and visualize Counter-Strike: Global Offensive (CSGO) demo files. You can visit the repository_ to view the source code, examples and data. Please join the Discord_ server if you would like to join our esports analytics community or to receive help with the library.

.. _repository: https://github.com/pnxenopoulos/csgo
.. _Discord: https://discord.gg/W34XjsSs2H

If you decide to use this library, please the following paper.

   Xenopoulos, P., Doraiswamy, H., & Silva, C. (2020, December). Valuing Player Actions in Counter-Strike: Global Offensive. In 2020 IEEE International Conference on Big Data (Big Data) (pp. 1283-1292). IEEE.

Using csgo
----------
:doc:`installation`
   How to install the csgo Python library.

:doc:`examples`
   Examples Jupyter notebooks to help get you started.

:doc:`projects`
   Projects that use the csgo Python library.

csgo Modules
------------
:doc:`analytics`
   Analytics module.

:doc:`data`
   Data module.

:doc:`parser`
   Parsing module.

:doc:`visualization`
   Visualization module.

.. Hidden TOCs

.. toctree::
   :caption: Getting Started
   :maxdepth: 2
   :hidden:

   installation
   examples
   projects

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   analytics
   data
   parser
   visualization
