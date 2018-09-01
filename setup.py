# -*- coding: utf-8 -*-
from setuptools import setup

with open('README.rst') as fd:
    long_description = fd.read()

setup(
    name='papis-zotero',
    version='0.0.2',
    author='Alejandro Gallo',
    author_email='aamsgallo@gmail.com',
    license='GPLv3',
    url='https://github.com/papis/papis-zotero',
    install_requires=[
        "papis>=0.7",
    ],
    classifiers=[
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
    ],
    description='Interact with zotero using papis',
    long_description=long_description,
    keywords=[
        'papis', 'zotero', 'bibtex',
        'management', 'cli', 'biliography'
    ],
    entry_points=dict(
        console_scripts=[
            'papis-zotero=papis_zotero:main'
        ]
    ),
    packages=['papis_zotero'],
    platforms=['linux', 'osx'],
)
