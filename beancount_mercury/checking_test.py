import io
import textwrap

import pytest  # NOQA, pylint: disable=unused-import
from beancount.ingest import extract

from . import CheckingImporter


def _unindent(indented):
    return textwrap.dedent(indented).lstrip()


def _stringify_directives(directives):
    f = io.StringIO()
    extract.print_extracted_entries(directives, f)
    return f.getvalue()


def test_identifies_mercury_file(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            02-04-2022,Joe Vendor,-550.00,Sent,Send Money transaction initiated on Mercury,"From Dummy, LLC for bowling balls",
            """))

    with mercury_file.open() as f:
        assert CheckingImporter(account='Assets:Checking:Mercury').identify(f)


def test_extracts_single_transaction_without_matching_account(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            02-04-2022,Joe Vendor,-550.00,Sent,Send Money transaction initiated on Mercury,"From Dummy, LLC for bowling balls",
            """))

    with mercury_file.open() as f:
        directives = CheckingImporter(
            account='Assets:Checking:Mercury').extract(f)

    assert _unindent("""
        2022-02-04 * "Joe Vendor" "Send Money transaction initiated on Mercury - From Dummy, LLC for bowling balls"
          Assets:Checking:Mercury  -550.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_single_transaction_with_matching_account(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            02-04-2022,Bowlers Paradise,-550.00,Sent,Send Money transaction initiated on Mercury,"From Dummy, LLC for bowling balls",
            """))

    with mercury_file.open() as f:
        directives = CheckingImporter(
            account='Assets:Checking:Mercury',
            account_patterns=[
                ('^Bowlers Paradise$',
                 'Expenses:Equipment:Bowling-Balls:Bowlers-Paradise')
            ]).extract(f)

    assert _unindent("""
        2022-02-04 * "Bowlers Paradise" "Send Money transaction initiated on Mercury - From Dummy, LLC for bowling balls"
          Assets:Checking:Mercury                            -550.00 USD
          Expenses:Equipment:Bowling-Balls:Bowlers-Paradise   550.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_matches_transactions_by_priority(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            02-04-2022,Bowlers Paradise,-550.00,Sent,Send Money transaction initiated on Mercury,"From Dummy, LLC for bowling balls",
            02-05-2022,Paradise Golf,-150.75,Sent,PARADISE GOLF,,
            """))

    with mercury_file.open() as f:
        directives = CheckingImporter(
            account='Assets:Checking:Mercury',
            account_patterns=[
                ('^Bowlers Paradise$',
                 'Expenses:Equipment:Bowling-Balls:Bowlers-Paradise'),
                ('Paradise', 'Expenses:Training:Paradise-Golf')
            ]).extract(f)

    assert _unindent("""
        2022-02-04 * "Bowlers Paradise" "Send Money transaction initiated on Mercury - From Dummy, LLC for bowling balls"
          Assets:Checking:Mercury                            -550.00 USD
          Expenses:Equipment:Bowling-Balls:Bowlers-Paradise   550.00 USD

        2022-02-05 * "Paradise Golf" "PARADISE GOLF"
          Assets:Checking:Mercury          -150.75 USD
          Expenses:Training:Paradise-Golf   150.75 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_incoming_transaction(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            01-30-2022,Charlie Customer,694.04,Sent,CHARLIE CUSTOMER,,
            """))

    with mercury_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Mercury',
                                      account_patterns=[
                                          ('^Charlie Customer$', 'Income:Sales')
                                      ]).extract(f)

    assert _unindent("""
        2022-01-30 * "Charlie Customer" "CHARLIE CUSTOMER"
          Assets:Checking:Mercury   694.04 USD
          Income:Sales             -694.04 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_ignores_failed_transaction(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            01-29-2021,Expensivo's Diamond Emporium,-5876.95,Failed,Expensivo's Diamond Emporium; TRANSACTION_BLOCKED --  C10 -- User is not allowed to send over 5000.0 per 1 day(s).,,
            """))

    with mercury_file.open() as f:
        directives = CheckingImporter(
            account='Assets:Checking:Mercury').extract(f)

    assert len(directives) == 0
