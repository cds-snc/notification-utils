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
        "bleach==3.3.0",
        "cachetools==4.2.1",
        "mistune==0.8.4",
        "requests==2.25.1",
        "python-json-logger==2.0.1",
        "Flask>=2.0.1",
        "orderedset==2.0.3",
        "markupsafe==2.0.1",
        "Jinja2==3.1.2",
        "statsd==3.3.0",
        "Flask-Redis==0.4.0",
        "PyYAML==5.4.1",
        "phonenumbers==8.12.21",
        "pytz==2021.3",
        "smartypants==2.0.1",
        "pypdf2==1.26.0",
        "py_w3c==0.3.1",
        # required by both api and admin
        "awscli==1.19.58",
        "boto3==1.17.58",
        "werkzeug==2.0.3",
        "mypy==0.961",
        "types-python-dateutil==2.8.17",
        "types-python-dateutil==2.8.17",
        "types-PyYAML==6.0.8",
        "types-pytz==2021.3.8",
        "types-bleach==5.0.2",
        "types-cachetools==5.0.1",
        "types-redis==4.2.6",
        "types-requests==2.27.30",
        "types-freezegun==1.1.9",
    ],
)
