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


def test_identifies_chase_file(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20211019.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,09/13/2021,"Online Transfer 12582403448 to Schwab Personal Checking ########1078 transaction #: 12582403448 09/13",-2500.00,ACCT_XFER,4325.75,,
            """))

    with chase_file.open() as f:
        assert CheckingImporter(account='Assets:Checking:Chase',
                                lastfour='1234').identify(f)


def test_extracts_outbound_transfer(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20211019.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,09/13/2021,"Online Transfer 12345678901 to Schwab Personal Checking ########9876 transaction #: 12345678901 09/13",-2500.00,ACCT_XFER,4325.75,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2021-09-13 * "Schwab Personal Checking ########9876" "Online Transfer 12345678901 to Schwab Personal Checking ########9876 Transaction #: 12345678901 09/13"
          Assets:Checking:Chase  -2500.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_same_day_ach_transaction(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20211019.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,05/24/2024,"Same-Day ACH Payment 12232800456 to JoeExample (_######9587)",-87.50,ACH_PAYMENT,6788.52,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2024-05-24 * "JoeExample" "Same-Day ACH Payment 12232800456 to JoeExample (_######9587)"
          Assets:Checking:Chase  -87.50 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_monthly_account_fee(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20230919.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,08/31/2023,"MONTHLY SERVICE FEE",-15.00,FEE_TRANSACTION,2118.39,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2023-08-31 * "Monthly Service Fee" ""
          Assets:Checking:Chase  -15.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_monthly_account_fee_refund(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20240309.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            CREDIT,02/01/2024,"Monthly Service Fee Reversal January 2024",15.00,REFUND_TRANSACTION,2521.99,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2024-02-01 * "Monthly Service Fee Reversal January 2024" ""
          Assets:Checking:Chase  15.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_real_time_payment_fee(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20240309.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,06/03/2024,"RTP/Same Day - Low Value",-1.75,FEE_TRANSACTION,6786.77,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2024-06-03 * "RTP/Same Day - Low Value" ""
          Assets:Checking:Chase  -1.75 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_doesnt_title_case_if_asked_not_to(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20230919.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,08/31/2023,"MONTHLY SERVICE FEE",-15.00,FEE_TRANSACTION,2118.39,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234',
                                      title_case=False).extract(f)

    assert _unindent("""
        2023-08-31 * "MONTHLY SERVICE FEE" ""
          Assets:Checking:Chase  -15.00 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_extracts_credit(tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20211019.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            CREDIT,09/03/2021,"ORIG CO NAME:gumroad.com            ORIG ID:1234567890 DESC DATE:       CO ENTRY DESCR:Gumroad   SEC:CCD    TRACE#:987654321987654 EED:112233   IND ID:ST-JAABBCCDDEEF              IND NAME:MICHAEL CUSTOMER TRN: 1122334455TC",63.84,ACH_CREDIT,7687.53,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234').extract(f)

    assert _unindent("""
        2021-09-03 * "gumroad.com" "Gumroad"
          Assets:Checking:Chase  63.84 USD
        """.rstrip()) == _stringify_directives(directives).strip()


def test_matches_account_when_pattern_splits_across_payee_and_narration(
        tmp_path):
    chase_file = tmp_path / 'Chase1234_Activity_20211019.CSV'
    chase_file.write_text(
        _unindent("""
            Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
            DEBIT,11/06/2021,"ORIG CO NAME:CHASE CREDIT CRD       ORIG ID:1234567890 DESC DATE:211203 CO ENTRY DESCR:AUTOPAYBUSSEC:PPD    TRACE#:987654321987654 EED:112233   IND ID:                             IND NAME:MICHAEL CUSTOMER T TRN: 1122334455TC",-357.51,ACH_DEBIT,2988.62,,
            """))

    with chase_file.open() as f:
        directives = CheckingImporter(account='Assets:Checking:Chase',
                                      lastfour='1234',
                                      account_patterns=[
                                          ('Chase Credit CRD.*Autopaybus',
                                           'Liabilities:Credit-Cards:Chase')
                                      ]).extract(f)

    assert _unindent("""
        2021-11-06 * "Chase Credit CRD" "Autopaybus"
          Assets:Checking:Chase           -357.51 USD
          Liabilities:Credit-Cards:Chase   357.51 USD
        """.rstrip()) == _stringify_directives(directives).strip()
