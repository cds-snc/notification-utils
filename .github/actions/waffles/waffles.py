#!/usr/bin/env python3

"""
Script to run reachability tests on AWS WAF using the project's endpoints.

The endpoints are determined with Flask's app configuration.

Usage:
    scripts/waffles.py list [options]
    scripts/waffles.py iron [options] [iron-option]

    Options:
    --app-libs=<libs_location>: Project's libs directory location.
    --app-loc=<location>:       Project's directory location.
    --flask-mod=<mod>:          Flask app module to execute.
    --flask-prop=<prop>:        Flask app property in the module.

    iron-option:
    --base-url=<url>:           Base URL used to hit the application with discovered Flask endpoints.

Example:
        waffles.py list --app-loc /Projects/cds/notification-document-download-api --app-lib doc-api-env/Lib/site-packages --flask-mod application --flask-prop application
        waffles.py iron --base-url=https://api.document.notification.canada.ca --app-loc /Projects/cds/notification-document-download-api --app-lib doc-api-env/Lib/site-packages --flask-mod application --flask-prop application
"""

import importlib
import importlib.util
import re
import sys
import urllib.parse
import uuid
from dataclasses import dataclass
from os.path import join
from pathlib import Path
from types import ModuleType
from typing import Any, List, NewType
from urllib import request
from urllib.error import URLError

from docopt import docopt
from flask import Flask
from notifications_utils.base64_uuid import uuid_to_base64

ModuleName = NewType("ModuleName", str)
ModuleProp = NewType("ModuleProp", str)
URL = NewType("URL", str)


@dataclass
class OptionsBase:
    app_libs: Path
    app_loc: Path
    flask_mod: ModuleName
    flask_prop: ModuleProp


@dataclass
class OptionsIron(OptionsBase):
    base_url: URL


@dataclass
class ValidationResult:
    base_url: URL


@dataclass
class OkValidationResult(ValidationResult):
    pass


@dataclass
class BadValidationResult(ValidationResult):
    exception: Exception


def _create_uuid() -> uuid.UUID:
    """Creates a valid UUID 4.

    Returns:
        uuid.UUID: A UUID
    """
    return uuid.uuid4()


def _display_flask_endpoints(flask_app: Flask) -> None:
    """Display Flask endpoints.

    Args:
        flask_app (Flask): A Flask app object.
    """
    output = []
    for rule in flask_app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        line = urllib.parse.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, rule))
        output.append(line)

    output = sorted(output)
    for extra_endpoint in flask_app.config.get("EXTRA_ROUTES", []):
        line = urllib.parse.unquote("EXTRA {:44s} {:20s} {}".format(extra_endpoint, "GET", extra_endpoint))
        output.append(line)

    for line in output:
        print(line)


def _get_flask_endpoints(flask_app: Flask) -> List[URL]:
    """Returns all endpoints registered within a Flask application.

    Args:
        flask_app (Flask): A Flask app object.

    Returns:
        List[URL]: List of URL endpoints.
    """
    endpoints: List[URL] = []
    for rule in flask_app.url_map.iter_rules():
        endpoint = URL(rule.rule)
        endpoints.append(endpoint)

    for extra_endpoint in flask_app.config.get("EXTRA_ROUTES", []):
        endpoint = URL(extra_endpoint)
        endpoints.append(endpoint)

    # Remove flask dynamic path
    if "/<path:path>" in endpoints:
        endpoints.remove("/<path:path>")

    return sorted(endpoints)


def _get_opts_base(args: dict) -> OptionsBase:
    """Get base parameters for this command.

    Args:
        args (dict): The arguments passed to this command.

    Returns:
        OptionsBase: Converted argumetns into an OptionsBase object.
    """
    return OptionsBase(
        app_libs=Path(args["--app-libs"]),
        app_loc=Path(args["--app-loc"]),
        flask_mod=ModuleName(args["--flask-mod"]),
        flask_prop=ModuleProp(args["--flask-prop"]),
    )


def _get_opts_iron(args: dict) -> OptionsIron:
    """Get Iron parameters for this command.

    Args:
        args (dict): The arguments passed to this command.

    Returns:
        OptionsIron: Converted argumetns into an OptionsIron object.
    """
    return OptionsIron(
        app_libs=Path(args["--app-libs"]),
        app_loc=Path(args["--app-loc"]),
        flask_mod=ModuleName(args["--flask-mod"]),
        flask_prop=ModuleProp(args["--flask-prop"]),
        base_url=URL(args["--base-url"]),
    )


def _hit_endpoints(flask_app: Flask, base_url: URL) -> List[ValidationResult]:
    """Hits the endpoints declared within the Flask app.

    If an endpoint contains variable in its declared route, the logic
    applies some transformations to replace with realistic value. It
    does not matter if the value would hit something existing as only
    the reachability of the URL is desired: if it fails, it means it
    is reachable and a success.

    Args:
        flask_app (Flask): A Flask application object.
        base_url (URL): The base URL to prepend to the supported Flask endpoints.

    Returns:
        List[ValidationResult]: List of results from hitting the endpoints.
    """
    validations: List[ValidationResult] = []
    partials = _get_flask_endpoints(flask_app)
    for partial in partials:
        endpoint = URL(f"{base_url}{partial}")
        endpoint = _transform_endpoint(endpoint)
        validation = _validate_waf_endpoint(endpoint)
        validations.append(validation)
    return validations


def _load_module(path_mod: Path, mod_filename: str) -> ModuleType:
    """
    Dynamically loads a module from a path and a module's filemame.

    Args:
        path_mod (Path): Module's path.
        mod_filename (str): Module's filename.

    Returns:
        ModuleType: The loaded module.
    """
    mod_name = mod_filename[:-3]
    path_full = join(path_mod, mod_filename)
    spec = importlib.util.spec_from_file_location(mod_name, path_full, submodule_search_locations=[])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_prop(path_app: Path, module_name: ModuleName, module_prop: ModuleProp) -> Any:
    """
    Dynamically loads a property from a module.

    Args:
        path_app (Path): Module's path.
        module_name (ModuleName): Module's name.
        module_prop (ModuleProp): Module's property.

    Returns:
        Any: The loaded module's property.
    """
    module_file = f"{module_name}.py"
    module = _load_module(path_app, module_file)
    return getattr(module, module_prop)


def _load_flask_app(path_app: Path, loc_libs: Path, module_name: ModuleName, module_prop: ModuleProp) -> Flask:
    """Returns a Flask app object located in a Flask project.

    Args:
        path_app (Path): The Flask application's path.
        loc_libs (Path): The Flask library locations from within the path.
        module_name (ModuleName): The module name containing the Flask application.
        module_prop (ModuleProp): The property within the module targeting the Flask application.

    Returns:
        Flask: A Flask app object.
    """
    path_libs = Path(join(path_app, loc_libs))
    _load_sys(path_libs)
    _load_sys(path_app)
    flask_app = _load_prop(path_app, module_name, module_prop)
    return flask_app


def _load_sys(path: Path) -> None:
    """Loads a system path into the current Python environment.

    To add the Flask modules and its library dependencies, this function
    can be used to add necessary paths into the current environment for
    Python to properly load dependent modules.

    Args:
        path (Path): The system path to load.
    """
    sys.path.insert(0, str(path))


def _transform_endpoint(endpoint: URL) -> URL:
    """Transforms a URL endpoint containing variable with realistic values.

    Args:
        endpoint (URL): The URL to transform.

    Returns:
        URL: The transformed URL.
    """
    endpoint = URL(re.sub(r"<uuid:[^>]*>", str(_create_uuid()), endpoint))
    endpoint = URL(re.sub(r"<base64_uuid:[^>]*>", str(uuid_to_base64(_create_uuid())), endpoint))
    endpoint = URL(endpoint.replace("<path:filename>", "filename.txt"))
    return endpoint


def _validate_waf_endpoint(endpoint: URL) -> ValidationResult:
    """Validates a URL endpoint.

    The validation logic needs to return a success if the endpoint
    is reachable and was declared from within the Flask application.

    The validation logic needs to return a failure if an endpoint was
    declared but is not reachable via a `204` HTTP status.

    Args:
        endpoint (URL): The endpoint to test.

    Returns:
        ValidationResult: Either a BadValidationResult or OkValidationResult.
    """
    print(f"Hitting endpoint '{endpoint}'... ", end="")
    req = request.Request(endpoint, method="HEAD")
    try:
        response = request.urlopen(req)
        status = response.getcode()
        if status == 204:
            print("WAF failure!")
            return BadValidationResult(endpoint, Exception("204 - AWS WAF blocked the request!"))
        else:
            print("OK.")
            return OkValidationResult(endpoint)
    except URLError:
        print("OK.")
        # Totally ok to get a bad request or something here. We don't have a JWT or api key.
        return OkValidationResult(endpoint)


def iron(opts: OptionsIron) -> None:
    """Validates that all Flask endpoints of a project are accessible by AWS WAF.

    Args:
        opts (OptionsIron): The command parameters.
    """
    flask_app = _load_flask_app(opts.app_loc, opts.app_libs, opts.flask_mod, opts.flask_prop)
    validations = _hit_endpoints(flask_app, opts.base_url)
    failures = list(filter(lambda v: isinstance(v, BadValidationResult), validations))
    if failures:
        print("\nA few endpoints could not be hit!")
        print("\nFailures are: {failures}".format(failures=failures))
        sys.exit(1)


def list_endpoints(opts: OptionsBase) -> None:
    """List all Flask endpoints of a project.

    Args:
        opts (OptionsBase): The command parameters.
    """
    flask_app = _load_flask_app(opts.app_loc, opts.app_libs, opts.flask_mod, opts.flask_prop)
    _display_flask_endpoints(flask_app)


def main():
    args = docopt(__doc__)
    if args["list"]:
        list_endpoints(_get_opts_base(args))
    elif args["iron"]:
        iron(_get_opts_iron(args))
    else:
        print("command not found")


if __name__ == "__main__":
    main()
