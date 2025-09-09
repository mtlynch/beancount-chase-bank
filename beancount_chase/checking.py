import csv
import datetime
import os
import re

import titlecase
from beancount.core import amount
from beancount.core import data
from beancount.core import flags
from beancount.core import number as beancount_number
from beancount.ingest import importer

_COLUMN_DATE = 'Posting Date'
_COLUMN_PAYEE = 'Description'
_COLUMN_AMOUNT = 'Amount'
_COLUMN_TYPE = 'Type'

_FILENAME_PATTERN = re.compile(r'Chase(\d{4})_Activity_[\d_]{8}.*\.CSV',
                               re.IGNORECASE)


class CheckingImporter(importer.ImporterProtocol):

    def __init__(self,
                 account,
                 lastfour=None,
                 currency='USD',
                 account_patterns=None,
                 title_case=True):
        self._account = account
        self._last_four_account_digits = lastfour
        self._currency = currency
        self._account_patterns = []
        self._title_case = title_case
        if account_patterns:
            for pattern, account_name in account_patterns:
                self._account_patterns.append(
                    (_compile_regex(pattern), account_name))

    def _parse_amount(self, amount_raw):
        return amount.Amount(beancount_number.D(amount_raw), self._currency)

    def file_date(self, file):
        return max(map(lambda x: x.date, self.extract(file)))

    def file_account(self, _):
        return self._account

    def identify(self, file):
        match = _FILENAME_PATTERN.match(os.path.basename(file.name))
        if not match:
            return False
        return self._last_four_account_digits == match.group(1)

    def extract(self, f):
        transactions = []

        with open(f.name, encoding='utf-8') as csv_file:
            for index, row in enumerate(csv.DictReader(csv_file)):
                metadata = data.new_metadata(f.name, index)
                transaction = self._extract_transaction_from_row(row, metadata)
                if not transaction:
                    continue
                transactions.append(transaction)

        return transactions

    def _extract_transaction_from_row(self, row, metadata):
        transaction_date = datetime.datetime.strptime(row[_COLUMN_DATE],
                                                      '%m/%d/%Y').date()
        payee, transaction_description = _parse_payee(row[_COLUMN_PAYEE],
                                                      row[_COLUMN_TYPE])
        if payee:

            def abbreviations(word, **_):
                if word.upper() == 'ACH':
                    return word.upper()
                if word.upper() == 'PMNTS':
                    return 'Payments'
                if word.upper() == 'FX':
                    return 'Foreign Exchange'
                return None

            payee = titlecase.titlecase(
                payee, callback=abbreviations) if self._title_case else payee
        else:
            raise ValueError(
                f'failed to parse {_COLUMN_PAYEE}={row[_COLUMN_PAYEE]}, '
                f'{_COLUMN_TYPE}={row[_COLUMN_TYPE]}')
        if transaction_description:
            narration = (titlecase.titlecase(transaction_description)
                         if self._title_case else transaction_description)
        else:
            narration = None
        if row[_COLUMN_AMOUNT]:
            transaction_amount = self._parse_amount(row[_COLUMN_AMOUNT])
        else:
            return None  # 0 dollar transaction

        if transaction_amount == amount.Amount(beancount_number.D(0),
                                               self._currency):
            return None

        postings = [
            data.Posting(account=self._account,
                         units=transaction_amount,
                         cost=None,
                         price=None,
                         flag=None,
                         meta=None)
        ]
        for pattern, account_name in self._account_patterns:
            if _pattern_matches_transaction(pattern, payee, narration):
                postings.append(
                    data.Posting(account=account_name,
                                 units=-transaction_amount,
                                 cost=None,
                                 price=None,
                                 flag=None,
                                 meta=None))
                break

        # For some reason, pylint thinks data.Transactions is not callable.
        # pylint: disable=not-callable
        return data.Transaction(
            meta=metadata,
            date=transaction_date,
            flag=flags.FLAG_OKAY,
            payee=payee,
            narration=narration,
            tags=data.EMPTY_SET,
            links=data.EMPTY_SET,
            postings=postings,
        )


def _compile_regex(pattern):
    return re.compile(pattern, re.IGNORECASE)


# Collection of regex patterns for parsing Chase transactions.
_TRANSACTION_PATTERNS = [
    # Debit card transaction.
    (_compile_regex(r'^DEBIT_CARD$'), lambda _, desc: (desc, None)),

    # ACH transaction with company name and description (full format).
    (_compile_regex(r'ORIG CO NAME:(.+?)\s*ORIG ID:.*DESC DATE:.*'
                    r'CO ENTRY DESCR:(.+?)\s*SEC:.*TRACE#:.*EED:.*'),
     lambda m, _: (m.group(1), m.group(2))),

    # ACH transaction with company name and description (simple format).
    (_compile_regex(r'ORIG CO NAME:(.+?)\s*CO ENTRY DESCR:(.+?)\s*SEC:'),
     lambda m, _: (m.group(1), m.group(2))),

    # Outbound transfer.
    (_compile_regex(r'Online Transfer \d+ to (.+?)\s*transaction #'),
     lambda m, desc: (m.group(1), desc)),

    # ACH payment.
    (_compile_regex(r'^[a-z-]+ ACH Payment \d+ to ([a-z]+) \(_#+\d+\)$'),
     lambda m, desc: (m.group(1), desc)),

    # Standard ACH fee.
    (_compile_regex(r'^STANDARD ACH PMNTS INITIAL FEE$'), lambda _, desc:
     (desc, None)),

    # Inbound transfer.
    (_compile_regex(r'Online Transfer \d+ from (.+?)\s*transaction #'),
     lambda m, desc: (m.group(1), desc)),

    # Monthly service fee.
    (_compile_regex(r'^MONTHLY SERVICE FEE$'), lambda _, desc: (desc, None)),

    # Monthly service fee reversal.
    (_compile_regex(r'^Monthly Service Fee Reversal '), lambda _, desc:
     (desc, None)),

    # Real-time payment fee.
    (_compile_regex(r'^RTP/'), lambda _, desc: (desc, None)),

    # Wire transfer.
    (_compile_regex('WIRE_OUTGOING'), lambda _, desc: (desc, None)),

    # Foreign exchange wire fee.
    (_compile_regex('ONLINE FX INTERNATIONAL WIRE FEE'), lambda _, desc:
     (desc, None)),

    # Fee reversal.
    (_compile_regex(r'^FEE REVERSAL$'), lambda _, desc: (desc, None))
]


def _parse_payee(description, transaction_type):
    """Parse payee and description from transaction details.

    Args:
        description: The transaction description string.
        transaction_type: The type of transaction.

    Returns:
        Tuple of (payee, description) strings or (None, None) if no transaction
        matches.
    """
    for pattern, handler in _TRANSACTION_PATTERNS:
        # Try matching on the description.
        match = pattern.search(description)
        if match:
            return handler(match, description)

        # If no match on description, try matching the transaction type.
        match = pattern.search(transaction_type)
        if match:
            return handler(match, description)

    return None, None


def _pattern_matches_transaction(pattern, payee, narration):
    """Check if a pattern matches any part of a transaction.

    Args:
        pattern: Compiled regex pattern to match against.
        payee: The transaction payee string.
        narration: The transaction narration string.

    Returns:
        True if pattern matches any target string.
    """
    if not payee:
        return False

    targets = [payee]
    if narration:
        targets.extend([narration, f'{payee}{narration}'])

    return any(pattern.search(target) for target in targets)
