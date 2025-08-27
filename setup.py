from setuptools import setup, find_packages
import dictsqlite

DESCRIPTION = "You can handle basic SQLite operations in Python like Dict."
NAME = 'DictSQLite'
AUTHOR = 'Disnana'
AUTHOR_EMAIL = 'support@disnana.com'
URL = 'https://github.com/disnana/DictSQLite'
LICENSE = 'MIT (Custom License with Specific Terms)'
DOWNLOAD_URL = 'https://github.com/disnana/DictSQLite'
VERSION = dictsqlite.main.__version__
PYTHON_REQUIRES = ">=3.6"

INSTALL_REQUIRES = [
    'portalocker',
    'cryptography'
    'pickle'
]

EXTRAS_REQUIRE = {

}

PACKAGES = find_packages(include=["dictsqlite", "dictsqlite.*"])

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: Other/Proprietary License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
]

with open('./Pypi.md', 'r', encoding="utf-8") as fp:
    readme = fp.read()
long_description = readme

setup(name=NAME,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      maintainer=AUTHOR,
      maintainer_email=AUTHOR_EMAIL,
      description=DESCRIPTION,
      long_description=long_description,
      license=LICENSE,
      url=URL,
      version=VERSION,
      download_url=DOWNLOAD_URL,
      python_requires=PYTHON_REQUIRES,
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      packages=PACKAGES,
      classifiers=CLASSIFIERS,
      keywords='sqlite, dict, database, dict_like, dict like, dictsqlite, dict like sqlite',
      long_description_content_type='text/markdown'
      )
