.. awpy documentation master file, created by
   sphinx-quickstart on Sun Jan 30 21:22:52 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Awpy
===================
|Discord| |Github| |Build| |License|

.. |Discord| image:: https://img.shields.io/discord/868146581419999232?color=blue&label=Discord&logo=discord
   :target: https://discord.gg/W34XjsSs2H
   
.. |Github| image:: https://img.shields.io/badge/github-repo-yellowgreen
   :target: https://github.com/pnxenopoulos/awpy
   
.. |Build| image:: https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml/badge.svg
   :target: https://github.com/pnxenopoulos/awpy/actions/workflows/build.yml
   
.. |License| image:: https://img.shields.io/badge/license-MIT-lightgrey
   :target: https://github.com/pnxenopoulos/awpy/blob/main/LICENSE
   
`Awpy` allows a user to parse, analyze and visualize Counter-Strike 2 demos. You can visit the repository_ to view the source code, examples and data. To install Awpy, run ``pip install awpy`` (Python >= 3.9). Please join the Discord_ server if you would like to join our esports analytics community or to receive help with using Awpy. You can get started with the following example:

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

You can take a look at the :doc:`examples/parse_demo` to see how to parse a demo and access the data.

.. Hidden TOCs

.. toctree::
   :caption: Getting Started
   :maxdepth: 2
   :hidden:

   installation
   faq
   license

.. toctree::
   :caption: Example Notebooks
   :maxdepth: 2
   :hidden:

   examples/parse_demo
   examples/parse_demo_cli
   examples/demo_stats
   examples/plot_demo
   examples/map_data

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   cli
   data
   demo
   plot
   stats
   vis
