# Notification - notifications-utils [BETA]
Shared python code for Notification

Provides logging utils etc.

## Installing

This is a [python](https://www.python.org/) application.

#### Python version
This is a python 3 application. It has not been run against any version of python 2.x

    brew install python3

#### Dependency management

This is done through [pip](https://pip.readthedocs.io) and [virtualenv](https://virtualenv.readthedocs.org/en/latest/). In practise we have used
[VirtualEnvWrapper](http://virtualenvwrapper.readthedocs.org/en/latest/command_ref.html) for our virtual environments.

Setting up a virtualenvwrapper for python3

    mkvirtualenv -p /usr/local/bin/python3 notifications-utils


The boostrap script will set the application up. *Ensure you have activated the virtual environment first.*

    ./scripts/bootstrap.sh

This will

* Use pip to install dependencies.

#### Tests

The `./scripts/run_tests.sh` script will run all the tests. [py.test](http://pytest.org/latest/) is used for testing.

Running tests will also apply syntax checking, using [pycodestyle](https://pypi.python.org/pypi/pycodestyle).

Additionally code coverage is checked via pytest-cov:

## Versioning

After making changes in this repo, complete the following steps to see those changes in `notification-api`. 
Note: to test locally before pushing, do steps #1 and #4 below and then follow instructions in the `notification-api` README.

1. Increment the version in `notifications_utils/version.py`.

2. Push this change.

3. Manually run `./scripts/push-tag.sh`, which will look at `version.py` and push a tag with that version.

4. In `notification-api`, update `requirements.txt` and `requirements-app.txt` to point at the newly generated tag.

5. Push this change. 

## Documentation

Documentation for the template used to render emails is in the [docs](./docs/README.md) folder.
