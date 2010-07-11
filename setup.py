#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='glamkit-smartlinks',
    version='0.6.0',
    description='Conditional wiki-style links to Django models.',
    author='Thomas Ashelford',
    author_email='thomas@interaction.net.au',
    url='http://glamkit.org/',
    packages=find_packages(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)