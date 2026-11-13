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

### Inline email images

`HTMLEmailTemplate(..., enable_inline_images=True)` renders controlled image
personalisation without enabling arbitrary HTML. Image values have this shape:

```python
values = {
    "usage_chart": {
        "document": {
            "inline_image": {
                "content_id": "server-generated-content-id",
                "alt_text": "Your usage increased from 10 to 15 units.",
            }
        }
    }
}
```

Put `((usage_chart))` on its own line in the body, outside links and conditionals.
The renderer emits an escaped `img` element with a `cid:` source; the sending
application must attach the matching scanned image in a `multipart/related`
MIME part. The option defaults to `False`. Other renderers use the alt text,
including plain-text emails and preheaders. No image bytes or download URLs
are required by this library. Browser previews need separate image-serving
support; CID URLs are for delivered email only.

Optional `display_size` in `inline_image` metadata accepts `"responsive"`
(the default, constrained to the content width) or `"original"` (native image
dimensions, no maximum width). Email clients may still scale or clip oversized
images; horizontal scrolling is not guaranteed.

Alternatively, `max_width` accepts a positive integer in pixels, applying a
pixel-width ceiling without enlarging smaller images and preserving aspect
ratio. It is mutually exclusive with `display_size`.
