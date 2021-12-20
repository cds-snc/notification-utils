#!/usr/bin/env python3

"""
Script to run reachability tests on AWS WAF using the project's endpoints.

The endpoints are determined with Flask's app configuration.

Usage:
    scripts/waffles.py list [options]
    scripts/waffles.py iron [options] [iron-option]

    Options:
    --app-libs=<libs_location>:  Project's libs directory location.
    --app-loc=<location>:        Project's directory location.
    --flask-mod=<mod>:           Flask app module to execute.
    --flask-prop=<prop>:         Flask app property in the module.

    iron-option:
    --base-url=<url>:       Hits the Flask endpoints and verify reachability.

Example:
        waffles.py list --app-loc /Projects/cds/notification-document-download-api --app-lib doc-api-env/Lib/site-packages --flask-mod application --flask-prop application
        waffles.py iron --base-url=https://api.document.notification.canada.ca --app-loc /Projects/cds/notification-document-download-api --app-lib doc-api-env/Lib/site-packages --flask-mod application --flask-prop application
"""

import importlib
import importlib.util
import os
import sys
import urllib.parse

from dataclasses import dataclass
from docopt import docopt
from flask import Flask
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules
from os.path import join
from types import ModuleType
from typing import Any, List, NewType, Optional
from urllib import request
from urllib.error import URLError
import uuid
import re


def create_uuid():
    return str(uuid.uuid4())


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


def _display_flask_endpoints(flask_app: Flask) -> None:
    output = []
    for rule in flask_app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        line = urllib.parse.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, rule))
        output.append(line)
    for line in sorted(output):
        print(line)


def _get_flask_endpoints(flask_app: Flask) -> List[URL]:
    endpoints: List[URL] = []
    for rule in flask_app.url_map.iter_rules():
        endpoint = URL(rule.rule)
        endpoints.append(endpoint)
    return sorted(endpoints)


def _get_opts_base(args: dict) -> OptionsBase:
    return OptionsBase(
        app_libs=Path(args["--app-libs"]),
        app_loc=Path(args["--app-loc"]),
        flask_mod=ModuleName(args["--flask-mod"]),
        flask_prop=ModuleProp(args["--flask-prop"]),
    )


def _get_opts_iron(args: dict) -> OptionsIron:
    return OptionsIron(
        app_libs=Path(args["--app-libs"]),
        app_loc=Path(args["--app-loc"]),
        flask_mod=ModuleName(args["--flask-mod"]),
        flask_prop=ModuleProp(args["--flask-prop"]),
        base_url=URL(args["--base-url"]),
    )


def _hit_endpoints(flask_app: Flask, base_url: URL) -> List[ValidationResult]:
    validations: List[ValidationResult] = []
    partials = _get_flask_endpoints(flask_app)
    for partial in partials:
        endpoint = URL(f"{base_url}{partial}")
        validation = _request(endpoint)
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
    path_libs = Path(join(path_app, loc_libs))
    _load_sys(path_libs)
    _load_sys(path_app)
    flask_app = _load_prop(path_app, module_name, module_prop)
    return flask_app


def _load_sys(path: Path) -> None:
    sys.path.insert(0, str(path))


def _request(endpoint: URL) -> ValidationResult:
    endpoint = re.sub(r"<uuid:[^>]*>", create_uuid(), endpoint)
    endpoint = endpoint.replace("<path:filename>", "filename.txt")

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
    except URLError as error:
        print("OK.")
        return OkValidationResult(endpoint)  # totally ok to get a bad request or something here. We don't have a JWT or api key


def iron(opts: OptionsIron) -> None:
    flask_app = _load_flask_app(opts.app_loc, opts.app_libs, opts.flask_mod, opts.flask_prop)
    validations = _hit_endpoints(flask_app, opts.base_url)
    failures = list(filter(lambda v: isinstance(v, BadValidationResult), validations))
    if failures:
        print("\nA few endpoints could not be hit!")
        sys.exit(1)


def list_endpoints(opts: OptionsBase) -> None:
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
