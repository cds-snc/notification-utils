"""
Python API client for GOV.UK Notify
"""
import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("notifications_utils/version.py", "rb") as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1)))  # type: ignore

setup(
    name="notifications-utils",
    version=version,
    url="https://github.com/alphagov/notifications-utils",
    license="MIT",
    author="Government Digital Service",
    description="Shared python code for GOV.UK Notify.",
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "bleach==4.1.0",
        "cachetools>=4.1.1",
        "mistune<2.0.0",
        "requests>=2.25.0",
        "python-json-logger>=2.0.1",
        "Flask>=1.1.1",
        "orderedset>=2.0.3",
        "markupsafe==2.0.1",
        "Jinja2==2.11.3",
        "statsd>=3.3.0",
        "Flask-Redis>=0.4.0",
        "PyYAML>=5.3.1",
        "phonenumbers>=8.12.13",
        "pytz>=2020.4",
        "smartypants>=2.0.1",
        "pypdf2>=1.27.5",
        "py_w3c==0.3.1",
        # required by both api and admin
        "awscli==1.19.58",
        "boto3==1.17.58",
    ],
)