# beancount-mercury

[![PyPI](https://img.shields.io/pypi/v/beancount-mercury)](https://pypi.org/project/beancount-mercury/)
[![CircleCI](https://circleci.com/gh/mtlynch/beancount-mercury.svg?style=svg)](https://circleci.com/gh/mtlynch/beancount-mercury)
[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](LICENSE)

beancount-mercury provides an Importer for converting CSV exports Mercury checking transactions into [Beancount](https://github.com/beancount/beancount) v2 format.

## Installation

```bash
pip install beancount-mercury
```

## Usage

Add the Mercury importer to your account as follows:

```python
import beancount_mercury

CONFIG = [
    beancount_mercury.CheckingImporter(
        'Assets:Checking:Mercury',
        currency='USD',
        account_patterns=[
          # These are example patterns. You can add your own.
          ('GITHUB', 'Expenses:Cloud-Services:Source-Hosting:Github'),
          ('Fedex',  'Expenses:Postage:FedEx'),
        ]
    ),
]
```

The `account_patterns` parameter is a list of (regex, account) pairs. For each line in your Mercury CSV, `CheckingImporter` will attempt to create a matching posting on the transaction by matching the payee or narration to the regexes. The regexes are in priority order, with earlier patterns taking priority over later patterns.

Once this configuration is in place, you can use `bean-extract` to convert a Mercury CSV export of transactions to beancount format:

```bash
bean-extract config.py mercury-transactions.csv
```

## Resources

See [awesome-beancount](https://awesome-beancount.com/) for other publicly available Beancount importers.
