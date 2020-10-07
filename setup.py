"""
Python API client for GOV.UK Notify
"""
import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('notifications_utils/version.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='notifications-utils',
    version=version,
    url='https://github.com/alphagov/notifications-utils',
    license='MIT',
    author='Government Digital Service',
    description='Shared python code for GOV.UK Notify.',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'bleach==3.2.1',
        'mistune==0.8.4',
        'requests==2.24.0',
        'python-json-logger==2.0.0',
        'Flask>=0.12.2',
        'orderedset==2.0.3',
        'Jinja2==2.11.2',
        'statsd==3.3.0',
        'Flask-Redis==0.4.0',
        'PyYAML==5.3.1',
        'phonenumbers==8.12.10',
        'pytz==2020.1',
        'smartypants==2.0.1',
        'monotonic==1.5',
        'pypdf2==1.26.0',

        # required by both api and admin
        'awscli==1.18.154',
        'boto3==1.15.13',
    ]
)
