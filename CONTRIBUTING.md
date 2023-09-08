# Contributing to awpy

Hi! We're happy to have you here. Thank you in advance for your contribution to awpy.

## Python code

To make sure that awpy code stays readable and works correctly, we are making use of a variety of helpful tools.

We use the following tools:

- [black](https://github.com/psf/black): An uncompromising Python code formatter.
- [ruff](https://github.com/astral-sh/ruff): An extremely fast Python linter, written in Rust.
- [pyright](https://github.com/microsoft/pyright): A static type checker for Python.
- [pylint](https://github.com/pylint-dev/pylint): A static code analyser for Python.
- [pytest](https://docs.pytest.org/en/7.4.x/): A mature full-featured Python testing tool.
- [pre-commit](https://pre-commit.com/): A framework for managing and maintaining multi-language pre-commit hooks.

Please install these tools before you open a pull request to ensure that your contributions are easy to review.

To install the aforementioned tools, simply run the following:
```shell
pip install -r tests/requirements.txt
pre-commit install --install-hooks
```

After you have made your changes locally, use these tools to surface bugs or code smells by running the following:

```shell
pre-commit run --all-files --show-diff-on-failure  # ruff, black, typos, pyright, pylint, golangci-lint
coverage run -m pytest --durations=10  # python tests
coverage report -m  # produces text-based coverage report
```

The coverage run -m pytest --durations=10 command, which runs the Python tests, can take a while as it has to not only download a handful of demos but also parse them. These tests must pass for a pull request to be merged into the main branch.

If you do not have the time or bandwidth, you can omit running the test command locally, since Github actions will run them, as well.

### Testing/Coverage

If you are fixing a bug or adding a new feature make sure to also add [unit tests](https://en.wikipedia.org/wiki/Unit_testing)
that cover the original bug or your new functionality.
If you are new to writing unit tests, look at the aforementioned link, or check out the [tests](tests) directory in awpy to see how our existing tests are built.

## Go code

If you are making changes or additions to the Go code then a look at and run
[golangci-lint](https://github.com/golangci/golangci-lint).

To install it, simply follow the [instructions](https://golangci-lint.run/usage/install/#local-installation) on their website.
To run it do the following:

```
cd awpy/parser  # Change into the directory containing the go files
golangci-lint run  # Run the linters
```

Additionally, run the Go code tests with:
```
go test -covermode=count -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
go test -fuzz=FuzzConvertRank -fuzztime 30s
go test -fuzz=FuzzDetermineSecond -fuzztime 30s
go test -fuzz=FuzzParseTeamBuy -fuzztime 30s
```

Don't forget to run the Python tests as explained above -- changes in the Go code likely change the JSON output!

If you are adding functionality aim to also add go tests to avoid bug and future regressions.

If you are adding a test that requires a specific demo, please let us know so that we can include them in our set of testing demos.
While developing, you can also edit the [test_data.json](/tests/test_data.json) file to include wherever you are hosting the test demo file.


## Thanks

With all this you are now ready to make contributions to awpy. We are looking forward to them!
