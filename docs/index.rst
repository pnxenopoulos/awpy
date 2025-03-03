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

.. |Artifacts| image:: https://github.com/pnxenopoulos/awpy/actions/workflows/artifacts.yml/badge.svg
   :target: https://github.com/pnxenopoulos/awpy/actions/workflows/artifacts.yml
   
.. |License| image:: https://img.shields.io/badge/license-MIT-lightgrey
   :target: https://github.com/pnxenopoulos/awpy/blob/main/LICENSE
   
`Awpy` (GitHub_) allows a user to parse, analyze and visualize Counter-Strike 2 demos, specifically those from competitive Counter-Strike (e.g., demos from HLTV, FACEIT, and competitive matchmaking). To install Awpy, run ``pip install awpy`` (Python >= 3.11). Please join the Discord_ server if you would like to discuss Awpy or esports analytics. You can get started with the following example:

.. _GitHub: https://github.com/pnxenopoulos/awpy
.. _Discord: https://discord.gg/W34XjsSs2H


.. code-block:: python

   from awpy import Demo

   # Construct and then parse a demo
   dem = Demo("natus-vincere-vs-virtus-pro-m1-overpass.dem")
   dem.parse()

   # Access various dictionaries & Polars dataframes
   dem.header
   dem.rounds
   dem.grenades
   dem.kills
   dem.damages
   dem.bomb
   dem.smokes
   dem.infernos
   dem.shots
   dem.ticks

   # If you need to change to a Pandas dataframe, you can do
   dem.ticks.to_pandas()

You can take a look at the :doc:`examples/parse_demo` to see how to parse a demo and access the data.

.. Hidden TOCs

.. toctree::
   :caption: Getting Started
   :maxdepth: 2
   :hidden:

   getting-started/installation
   getting-started/faq
   getting-started/license
   modules/parser_output

.. toctree::
   :caption: Example Notebooks
   :maxdepth: 2
   :hidden:

   examples/parse_demo
   examples/parse_demo_cli
   examples/demo_stats
   examples/plot_demo
   examples/visibility
   examples/nav

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   modules/cli
   modules/data
   modules/demo
   modules/nav
   modules/plot
   modules/stats
   modules/visibility
