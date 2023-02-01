# Notification - notifications-utils [BETA]
Shared python code for Notification

Provides logging utils etc.

## Installing

This is a [python](https://www.python.org/) application.

#### Python version
This is a python 3 application. It has not been run against any version of python 2.x

    brew install python3

#### Dependency management

This is done through [poetry](https://python-poetry.org/).

Setting up a virtualenvwrapper for python3

    mkvirtualenv -p /usr/local/bin/python3 notifications-utils


The boostrap script will set the application up. *Ensure you have activated the virtual environment first with `poetry shell` or prefix the command with `poetry run`*

    ./scripts/bootstrap.sh

This will

* Use poetry to install dependencies.

#### Tests

The `./scripts/run_tests.sh` script will run all the tests. [py.test](http://pytest.org/latest/) is used for testing.

Running tests will also apply syntax checking, using [pycodestyle](https://pypi.python.org/pypi/pycodestyle).

Additionally code coverage is checked via pytest-cov:

## Documentation

* [How to work with notification-utils](https://github.com/cds-snc/notification-utils/wiki/How-to-work-with-notification-utils-locally)
* Documentation for the template used to render emails is in the [docs](./docs/README.md) folder.
