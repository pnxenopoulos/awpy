Frequently Asked Questions (FAQs)
=================================

This is a nonexhaustive list of frequently asked questions.

**Q:** Do I need Golang to run this?
    You don't *need* Golang to install awpy or access any part of it. However, **you need Golang 1.16+ to parse demofiles using awpy**.

**Q:** The parser returns weird rounds or data!
    Please note that awpy parses *everything* in a demo. This means that you may have rounds from the warmup, rounds that may have ended in a draw, and other odd-looking rounds. Try parsing with `DemoParser.parse(clean=True)` or by using the `DemoParser.clean_rounds()` method to clean up the parsed rounds. Note that this is not going to be 100 percent perfect. If you still have bad data, ask in the `Discord <https://discord.gg/W34XjsSs2H>`_.

**Q:** Data I want is missing!
    Feel free to open an `issue <https://github.com/pnxenopoulos/awpy/issues>`_ or to ask in the `Discord <https://discord.gg/W34XjsSs2H>`_, and we can see if such a feature is possible.

**Q:** Where can I get documentation for the parsed data contains?
    Please look at :doc:`parser_output`.

**Q:** How can I calculate statistics like KAST%, Rating or ADR?
    Look at :doc:`analytics`, and in particular, `awpy.analytics.stats`.



