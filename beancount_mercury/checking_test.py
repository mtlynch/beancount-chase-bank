import io
import textwrap

import pytest  # NOQA, pylint: disable=unused-import
from beancount.ingest import extract

from .checking import MercuryCheckingImporter


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
        assert MercuryCheckingImporter(
            account='Assets:Checking:Mercury').identify(f)


def test_extracts_single_transaction_without_matching_account(tmp_path):
    mercury_file = tmp_path / 'transactions-dummy-to-feb052022.csv'
    mercury_file.write_text(
        _unindent("""
            Date,Description,Amount,Status,Bank Description,Reference,Note
            02-04-2022,Joe Vendor,-550.00,Sent,Send Money transaction initiated on Mercury,"From Dummy, LLC for bowling balls",
            """))

    with mercury_file.open() as f:
        directives = MercuryCheckingImporter(
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
        directives = MercuryCheckingImporter(
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
