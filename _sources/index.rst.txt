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
   
`awpy` allows a user to parse, analyze and visualize Counter-Strike: Global Offensive (CSGO) demo files. You can visit the repository_ to view the source code, examples and data. Please join the Discord_ server if you would like to join our esports analytics community or to receive help with the library. To install the library, run ``pip install awpy`` (Python >= 3.9).

.. _repository: https://github.com/pnxenopoulos/awpy
.. _Discord: https://discord.gg/W34XjsSs2H

Using this library to parse CSGO demos is as easy as the few lines of code shown below. To see what output looks like, check out :doc:`parser_output`.

.. code-block:: python

   from awpy.parser import DemoParser

   # Set the parse_rate equal to the tick rate at which you would like to parse the frames of the demo.
   # This parameter only matters if parse_frames=True
   # For reference, MM demos are usually 64 ticks, and pro/FACEIT demos are usually 128 ticks.
   demo_parser = DemoParser(demofile="og-vs-natus-vincere-m1-dust2.dem", 
                            demo_id="og-vs-natus-vincere", 
                            parse_frames=True,
                            parse_rate=128)


   # Parse the demofile, output results to dictionary with df name as key
   data = demo_parser.parse()


   # There are a variety of top level keys
   # You can view game rounds and events in 'gameRounds']
   data["matchID"]
   data["clientName"]
   data["mapName"]
   data["tickRate"]
   data["playbackTicks"]
   data["playbackFramesCount"]
   data["parsedToFrameIdx"]
   data["parserParameters"]
   data["serverVars"]
   data["matchPhases"]
   data["matchmakingRanks"]
   data["playerConnections"]
   data["gameRounds"] # From this value, you can extract player events via: data['gameRounds'][i]['kills'], etc.

   # You can also parse the data into dataframes using
   data_df = demo_parser.parse(return_type="df")

   # The parser also writes a JSON file of the output named demo_id.json


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
   faq
   license

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   analytics
   data
   parser
   visualization
