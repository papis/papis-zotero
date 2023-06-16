from setuptools import setup

with open("README.rst") as fd:
    long_description = fd.read()

setup(
    name="papis-zotero",
    version="0.1.2",
    author="Alejandro Gallo",
    author_email="aamsgallo@gmail.com",
    license="GPLv3",
    url="https://github.com/papis/papis-zotero",
    install_requires=[
        "papis==0.13",
    ],
    classifiers=[
        "Environment :: Console :: Curses",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: MacOS",
        "Operating System :: Microsoft",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
    description="Interact with Zotero using papis",
    long_description=long_description,
    keywords=[
        "bibtex",
        "biliography",
        "cli",
        "management",
        "papis",
        "zotero",
    ],
    extras_require={
        "develop": [
            "flake8",
            "flake8-bugbear",
            "flake8-quotes",
            "mypy>=0.7",
            "pep8-naming",
            "pytest",
            "pytest-cov",
            "python-coveralls",
            "types-PyYAML",
            "types-tqdm",
        ]
    },
    entry_points={
        "papis.command": [
            "zotero=papis_zotero:main"
        ]
    },
    packages=["papis_zotero"],
    platforms=["linux", "osx", "win32"],
)
