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
                    (re.compile(pattern, flags=re.IGNORECASE), account_name))

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
        payee, transaction_description = _parse_description(row[_COLUMN_PAYEE])
        if payee:
            payee = titlecase.titlecase(payee) if self._title_case else payee
        else:
            raise ValueError(f'failed to parse {row[_COLUMN_PAYEE]}')
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


_DESCRIPTION_PATTERN = re.compile(
    # pylint: disable=line-too-long
    r'ORIG CO NAME:(.+?)\s*ORIG ID:.*DESC DATE:.*CO ENTRY DESCR:(.+?)\s*SEC:.*TRACE#:.*EED:.*',
    re.IGNORECASE)

_OUTBOUND_TRANSFER_PATTERN = re.compile(
    r'Online Transfer \d+ to (.+?)\s*transaction #', re.IGNORECASE)

_SAME_DAY_ACH_PAYMENT_PATTERN = re.compile(
    r'^Same-Day ACH Payment \d+ to ([A-Za-z]+) \(_#+\d+\)$', re.IGNORECASE)

_INBOUND_TRANSFER_PATTERN = re.compile(
    r'Online Transfer \d+ from (.+?)\s*transaction #', re.IGNORECASE)

_MONTHLY_SERVICE_FEE_PATTERN = re.compile(r'^MONTHLY SERVICE FEE$',
                                          re.IGNORECASE)

_MONTHLY_SERVICE_FEE_REVERSAL_PATTERN = re.compile(
    r'^Monthly Service Fee Reversal ', re.IGNORECASE)

_REAL_TIME_PAYMENT_FEE_PATTERN = re.compile(r'^RTP/', re.IGNORECASE)


def _parse_description(description):
    match = _DESCRIPTION_PATTERN.search(description)
    if match:
        return match.group(1), match.group(2)
    match = _OUTBOUND_TRANSFER_PATTERN.search(description)
    if match:
        return match.group(1), description
    match = _SAME_DAY_ACH_PAYMENT_PATTERN.search(description)
    if match:
        return match.group(1), description
    match = _INBOUND_TRANSFER_PATTERN.search(description)
    if match:
        return match.group(1), description
    match = _MONTHLY_SERVICE_FEE_PATTERN.search(description)
    if match:
        return description, None
    match = _MONTHLY_SERVICE_FEE_REVERSAL_PATTERN.search(description)
    if match:
        return description, None
    match = _REAL_TIME_PAYMENT_FEE_PATTERN.search(description)
    if match:
        return description, None
    return None, None


def _pattern_matches_transaction(pattern, payee, narration):
    targets = [payee]
    if narration:
        targets.extend([narration, payee + narration])
    for target in targets:
        if pattern.search(target):
            return True
    return False
