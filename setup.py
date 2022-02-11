#!/usr/bin/env python

import os.path

import setuptools

setuptools.setup(
    name='beancount-chase-bank',
    long_description=open(
        os.path.join(os.path.abspath(os.path.dirname(__file__)),
                     'README.md')).read(),
    long_description_content_type="text/markdown",
    version='0.2.0',
    description='Import Chase banking transactions into beancount format',
    author='Michael Lynch',
    license="MIT",
    keywords="chase beancount bookkeeping finance",
    url='https://github.com/mtlynch/beancount-chase.git',
    packages=['beancount_chase'],
    install_requires=[],
    python_requires='>=3.7',
)
