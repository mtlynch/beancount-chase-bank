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

_COLUMN_DATE = 'Date'
_COLUMN_PAYEE = 'Description'
_COLUMN_DESCRIPTION = 'Bank Description'
_COLUMN_REFERENCE = 'Reference'
_COLUMN_AMOUNT = 'Amount'
_COLUMN_STATUS = 'Status'

_FILENAME_PATTERN = re.compile(r'transactions-.+\.CSV', re.IGNORECASE)


class MercuryCheckingImporter(importer.ImporterProtocol):

    def __init__(self, account, currency='USD', account_patterns=None):
        self._account = account
        self._currency = currency
        self._account_patterns = []
        if account_patterns:
            for pattern, account_name in account_patterns:
                self._account_patterns.append(
                    (re.compile(pattern, flags=re.IGNORECASE), account_name))

    def _parse_amount(self, amount_raw):
        return amount.Amount(beancount_number.D(amount_raw.replace('$', '')),
                             self._currency)

    def file_date(self, file):
        return max(map(lambda x: x.date, self.extract(file)))

    def file_account(self, _):
        return self._account

    def identify(self, file):
        return _FILENAME_PATTERN.match(os.path.basename(file.name))

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
        if row[_COLUMN_STATUS] and row[_COLUMN_STATUS] == 'Failed':
            return None
        transaction_date = datetime.datetime.strptime(row[_COLUMN_DATE],
                                                      '%m-%d-%Y').date()

        payee = titlecase.titlecase(row[_COLUMN_PAYEE])

        narration_list = []
        description = row[_COLUMN_DESCRIPTION]
        if description:
            narration_list.append(description)
        reference = row[_COLUMN_REFERENCE]
        if reference:
            narration_list.append(reference)
        narration = ' - '.join(narration_list)

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
            if pattern.search(payee) or pattern.search(narration):
                postings.append(
                    data.Posting(account=account_name,
                                 units=-transaction_amount,
                                 cost=None,
                                 price=None,
                                 flag=None,
                                 meta=None))

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
