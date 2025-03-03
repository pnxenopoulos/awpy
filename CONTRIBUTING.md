# Contributing to Awpy

Hi! We're happy to have you here. Thank you for considering making a contribution to Awpy. Contributions come in various forms -- from bug reports, to writing example documentation, to proposing and implementin gnew features. This is a guide on how to make contributions to Awpy. If you have any bugs or feature requests, please use [GitHub Issues](https://github.com/pnxenopoulos/awpy/issues). Otherwise, please keep reading.

## Python code

To make sure that Awpy code stays readable and works correctly, we are making use of a variety of helpful tools.

We use the following tools:

- [uv](https://docs.astral.sh/uv/): An extremely fast Python package and project manager, written in Rust.
- [ruff](https://github.com/astral-sh/ruff): An extremely fast Python linter, written in Rust.
- [pytest](https://docs.pytest.org): A mature full-featured Python testing tool.
- [pre-commit](https://pre-commit.com/): A framework for managing and maintaining multi-language pre-commit hooks.

Please install these tools before you begin to develop. After you've installed `uv`, you can run

```shell
uv sync --all-groups
uv tool install .
```

To install the dependencies. If you want to run Awpy cli commands, you'd do `uv run awpy ...`. To run other commands, you can do `uv run ruff format .` or `uv run pytest .`

To install the pre-commit hooks, you can run `uv run pre-commit install`

After you have made your changes locally, use these tools to surface bugs or code smells by running the following:

```shell
uv run pre-commit run --all-files --show-diff-on-failure  # ruff, typos, uv
uv run coverage run -m pytest --durations=10  # python tests
uv run coverage report -m  # produces text-based coverage report
```

The coverage run -m pytest --durations=10 command, which runs the Python tests, can take a while as it has to not only download a handful of demos but also parse them. These tests *must pass* for a pull request to be merged into the main branch.

If you do not have the time or bandwidth, you can omit running the test command locally, since Github actions will run them, as well.

### Testing/Coverage

If you are fixing a bug or adding a new feature, we highly recommend you add [unit tests](https://en.wikipedia.org/wiki/Unit_testing) that cover the original bug or your new functionality. If you are new to writing unit tests, look at the aforementioned link, or check out the [tests](tests) directory in Awpy to see how our existing tests are built.

If you are adding a test that requires a specific demo, please let us know so that we can include them in our set of testing demos, which is located in the [test_data.json](/tests/test_data.json) file.

You need `pandoc` to build the documentation locally. On Linux, you can install it with `sudo apt install pandoc`.

### Game Updates
During game updates, we may need to update .nav, .tri, map images and map data. The scripts to do these are located in `scripts/` and depend on the [Source2Viewer CLI](https://valveresourceformat.github.io/). Specifically, you can look at the `artifacts.yml` workflow to see how this process is automated.

## Thanks
With all this, you are now ready to make contributions to Awpy. Many users depend on your contributions. We look forward to your help!
