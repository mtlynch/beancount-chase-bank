import io
import textwrap

import pytest  # NOQA, pylint: disable=unused-import
from beancount.ingest import extract

from . import CreditImporter


def _unindent(indented):
    return textwrap.dedent(indented).lstrip()


def _stringify_directives(directives):
    f = io.StringIO()
    extract.print_extracted_entries(directives, f)
    return f.getvalue()


def test_identifies_chase_credit_file(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,01/06/2021,01/07/2021,AMZN Mktp US,Shopping,Sale,-20.54,
            """))

    with chase_file.open() as f:
        assert CreditImporter(account='Liabilities:Credit-Cards:Chase',
                              lastfour='1234').identify(f)


def test_identifies_chase_credit_file_first_statement(tmp_path):
    """The first statement in an account has a shorter filename."""
    chase_file = tmp_path / 'Chase1234_Activity20220720.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,01/06/2021,01/07/2021,AMZN Mktp US,Shopping,Sale,-20.54,
            """))

    with chase_file.open() as f:
        assert CreditImporter(account='Liabilities:Credit-Cards:Chase',
                              lastfour='1234').identify(f)


def test_extracts_spend(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,10/29/2021,10/31/2021,GOOGLE *CLOUD_02BB66-C,Professional Services,Sale,-25.35,
            """))

    with chase_file.open() as f:
        directives = CreditImporter(account='Liabilities:Credit-Cards:Chase',
                                    lastfour='1234').extract(f)

    assert _unindent("""
        2021-10-29 * "Google *Cloud_02bb66-C"
          Liabilities:Credit-Cards:Chase  -25.35 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_spend_with_matching_transaction(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,10/29/2021,10/31/2021,GOOGLE *CLOUD_02BB66-C,Professional Services,Sale,-25.35,
            """))

    with chase_file.open() as f:
        directives = CreditImporter(
            account='Liabilities:Credit-Cards:Chase',
            lastfour='1234',
            account_patterns=[
                ('Google.*Cloud',
                 'Expenses:Cloud-Services:Google-Cloud-Platform'),
            ]).extract(f)

    assert _unindent("""
        2021-10-29 * "Google *Cloud_02bb66-C"
          Liabilities:Credit-Cards:Chase                 -25.35 USD
          Expenses:Cloud-Services:Google-Cloud-Platform   25.35 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_doesnt_title_case_if_asked_not_to(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,10/29/2021,10/31/2021,GOOGLE *CLOUD_02BB66-C,Professional Services,Sale,-25.35,
            """))

    with chase_file.open() as f:
        directives = CreditImporter(
            account='Liabilities:Credit-Cards:Chase',
            lastfour='1234',
            account_patterns=[
                ('Google.*Cloud',
                 'Expenses:Cloud-Services:Google-Cloud-Platform'),
            ],
            title_case=False).extract(f)

    assert _unindent("""
        2021-10-29 * "GOOGLE *CLOUD_02BB66-C"
          Liabilities:Credit-Cards:Chase                 -25.35 USD
          Expenses:Cloud-Services:Google-Cloud-Platform   25.35 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_refund(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,01/06/2021,01/07/2021,AMZN Mktp US,Shopping,Return,413.54,
            """))

    with chase_file.open() as f:
        directives = CreditImporter(account='Liabilities:Credit-Cards:Chase',
                                    lastfour='1234').extract(f)

    assert _unindent("""
        2021-01-06 * "AMZN MKTP US"
          Liabilities:Credit-Cards:Chase  413.54 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_payment(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity20210103_20210202_20210214.CSV'
    chase_file.write_text(
        _unindent("""
            Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
            1234,11/04/2021,11/04/2021,Payment Thank You - Web,,Payment,4000.00,
            """))

    with chase_file.open() as f:
        directives = CreditImporter(account='Liabilities:Credit-Cards:Chase',
                                    lastfour='1234',
                                    account_patterns=[
                                        ('Payment Thank You',
                                         'Assets:Checking:Bank-of-America')
                                    ]).extract(f)

    assert _unindent("""
        2021-11-04 * "Payment Thank You - Web"
          Liabilities:Credit-Cards:Chase    4000.00 USD
          Assets:Checking:Bank-of-America  -4000.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()
