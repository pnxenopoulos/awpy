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
   
.. |Licence| image:: https://img.shields.io/badge/license-MIT-lightgrey
   :target: https://github.com/pnxenopoulos/awpy/blob/main/LICENSE
   
`awpy` allows a user to parse, analyze and visualize Counter-Strike demo files. You can visit the repository_ to view the source code, examples and data. Please join the Discord_ server if you would like to join our esports analytics community or to receive help with the library. To install the library, run ``pip install awpy`` (Python >= 3.11).

.. _repository: https://github.com/pnxenopoulos/awpy
.. _Discord: https://discord.gg/W34XjsSs2H

Using Awpy to parse Counter-Strike demos is as easy as the few lines of code shown below. To see what output looks like, check out :doc:`parser_output`.

.. code-block:: python

   from awpy import parse_demo

   # Parse a demo file in one line!
   demo = parse_demo(file="og-vs-natus-vincere-m1-dust2.dem")

   # The `demo` object contains a variety of keys
   demo.header       # Header information like the map, tick rate, etc.
   demo.rounds       # A list of rounds and their start/end ticks
   demo.kills        # Kills and their details
   demo.damages      # Damage dealt by each player
   demo.grenades     # Grenade throws and their trajectories
   demo.effects      # Smokes & mollies
   demo.flashes      # When a player is flashed
   demo.weapon_fires # Shots fired by each player
   demo.bomb_events  # Include plants, defuses, plant_start, defuse_start, etc.
   demo.ticks        # A list of each player's info at each tick


Using awpy
----------
:doc:`installation`
   How to install `awpy`.

:doc:`examples`
   Examples code and Jupyter notebooks to help get you started.

:doc:`projects`
   Projects that use `awpy`.

:doc:`faq`
   Need help? Check the FAQs first.

:doc:`license`
   License and acknowledgments.

awpy Modules
------------
:doc:`data`
   Data module.

:doc:`parser`
   Parsing module.

:doc:`stats`
   Stats module.

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
