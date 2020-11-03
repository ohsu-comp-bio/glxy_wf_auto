#!/usr/bin/env python

from __future__ import print_function

import io
import os
import re

from setuptools import setup, find_packages


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="glxy_wf",
    version=find_version("glxy_wf", "__init__.py"),
    description="",
    author="OHSU Computational Biology",
    author_email="creason@ohsu.edu",
    url="https://github.com/ohsu-comp-bio/glxy_wf_auto",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.5",
    install_requires=[
      "bioblend==0.10.0",
      "boto==2.48.0",
      "certifi==2018.1.18",
      "chardet==3.0.4",
      "dynamic-yaml==1.2.3",
      "idna==2.6",
      "python-dotenv==0.8.2",
      "pandas==0.23.4",
      "requests==2.18.4",
      "requests-toolbelt==0.8.0",
      "six==1.11.0",
      "urllib3==1.22",
      "coloredlogs==9.0",
      "jq==2.11.1",
    ],
    entry_points={
        "console_scripts": ["glxy_wf=glxy_wf.__main__:main"]},
    zip_safe=True,
    classifiers=[],
)
