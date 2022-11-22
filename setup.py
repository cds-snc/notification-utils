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
        "bleach==3.3.1",
        "cachetools==4.2.4",
        "mistune==0.8.4",
        "requests==2.28.1",
        "python-json-logger==2.0.4",
        "Flask==2.2.2",
        "orderedset==2.0.3",
        "markupsafe==2.1.1",
        "Jinja2>3.0.0",
        "statsd==3.3.0",
        "Flask-Redis==0.4.0",
        "PyYAML==5.4.1",
        "phonenumbers==8.13.0",
        "pytz==2021.3",
        "smartypants==2.0.1",
        "pypdf2==1.28.6",
        "py_w3c==0.3.1",
        # required by both api and admin
        "awscli==1.27.10",
        "boto3==1.26.10",
        "werkzeug==2.2.2",
        "itsdangerous==2.1.2",
    ],
)
