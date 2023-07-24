# Contributing to awpy

Hi! We're happy to have you here. Thank you in advance for your contribution to awpy.

## Python code

To make sure that awpy code stays readeable and works correctly we are making use of
a variaty of helpfull tools.

At the time of writing these are:

- [black](https://github.com/psf/black): An uncompromising Python code formatter.
- [ruff](https://github.com/astral-sh/ruff): An extremely fast Python linter, written in Rust.
- [pyright](https://github.com/microsoft/pyright): A static type checker for Python.
- [pylint](https://github.com/pylint-dev/pylint): A static code analyser for Python.
- [pytest](https://docs.pytest.org/en/7.4.x/): A mature full-featured Python testing tool.
- [pre-commit](https://pre-commit.com/): A framework for managing and maintaining multi-language pre-commit hooks.

To make sure that you pull request is easy to review and can be merged quickly please
please install these after cloning the repo.

For that simply run the following commands:
```shell
pip install -r tests/requirements.txt
pre-commit install --install-hooks
```

After you have made your changes locally run these tools to make sure there are no
bugs or code smells have snook in. This can be done by running:

```shell
pre-commit run --all-files --show-diff-on-failure  # black formatting, ruff linting
pyright  # type checking
pylint awpy  # more linting
coverage run -m pytest --durations=10  # python tests
coverage report -m
```

The test part can take a while as it has to download a handful of demos to make sure
that the parser is working correctly for all kinds of platforms and edge cases.

If you do not have the time or bandwidth you can omit this part if absolutely necessary.
The continous integration setup on GitHub will then run these for you.

### Testing/Coverage

If you are fixing a bug or adding a new feature make sure to also add [unit tests](https://en.wikipedia.org/wiki/Unit_testing)
that cover the original bug or your new functionality. If you are new to that have a
look at the pytest documentation linked above. You can also check out the [tests](tests)
directory in awpy to see how the existing code is being tested.

## Go code

If you are making changes or additions to the Go code then a look at and run
[golangci-lint](https://github.com/golangci/golangci-lint).

To install it simply follow the [instructions](https://golangci-lint.run/usage/install/#local-installation) on their website.
To run it do the following:

```
cd awpy/parser  # Change into the directory containing the go files
golangci-lint run  # Run the linters
```

Additionally run the tests of the go code via:
```
go test -covermode=count -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
go test -fuzz=FuzzConvertRank -fuzztime 30s
go test -fuzz=FuzzDetermineSecond -fuzztime 30s
go test -fuzz=FuzzParseTeamBuy -fuzztime 30s
```

Do not forget to also run the python tests as explained above.

If you are adding functionality aim to also add go tests to avoid bug and future regressions.
In case changes to the go code were required to make sure it does not crash on certain
kinds of demos please also add unit tests for these demos in the python tests.

For us to run these tests ourselves to verify the results and make sure no future changes
break you fix again please also upload the demo(s) to a file sharing service so that
we can include them in our [set of testing demos](/tests/test_data.json).
You can also already prefill this file and use the link to your file hoster as a
temporary place holder.


## Thanks

With all this you are now ready to make contributions to awpy. We are looking forward to them!
