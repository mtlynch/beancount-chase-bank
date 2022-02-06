# beancount-chase-bank

[![PyPI](https://img.shields.io/pypi/v/beancount-chase-bank)](https://pypi.org/project/beancount-chase-bank/)
[![CircleCI](https://circleci.com/gh/mtlynch/beancount-chase-bank.svg?style=svg)](https://circleci.com/gh/mtlynch/beancount-chase-bank)
[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](LICENSE)

beancount-chase-bank provides an Importer for converting CSV exports Chase bank transactions into [Beancount](https://github.com/beancount/beancount) v2 format.

## Installation

```bash
pip install beancount-chase-bank
```

## Usage

Add the Chase Checking importer to your account as follows:

```python
import beancount_chase

CONFIG = [
    beancount_chase.CheckingImporter(
        'Assets:Checking:Chase',
        currency='USD',
        lastfour='1234', # Replace with last four digits of your account
        account_patterns=[
          # These are example patterns. You can add your own.
          ('GITHUB', 'Expenses:Cloud-Services:Source-Hosting:Github'),
          ('Fedex',  'Expenses:Postage:FedEx'),
        ]
    ),
]
```

The `account_patterns` parameter is a list of (regex, account) pairs. For each line in your Chase CSV, `CheckingImporter` will attempt to create a matching posting on the transaction by matching the payee or narration to the regexes. The regexes are in priority order, with earlier patterns taking priority over later patterns.

Once this configuration is in place, you can use `bean-extract` to convert a Chase CSV export of transactions to beancount format:

```bash
bean-extract config.py Chase1234_Activity_20220219.CSV
```

## Resources

See [awesome-beancount](https://awesome-beancount.com/) for other publicly available Beancount importers.
