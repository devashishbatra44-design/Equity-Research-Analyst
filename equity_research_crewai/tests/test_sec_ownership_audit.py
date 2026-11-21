from __future__ import annotations

from datetime import date

from equity_research_crewai.sec_ownership_audit import audit_issuer


class StubClient:
    def get_json(self, _url: str) -> dict:
        return {
            "filings": {
                "recent": {
                    "form": ["4", "8-K", "4/A"],
                    "filingDate": ["2026-11-18", "2026-11-19", "2026-11-20"],
                    "accessionNumber": ["0001-26-000001", "0001-26-000002", "0001-26-000003"],
                    "primaryDocument": ["one.xml", "two.htm", "three.xml"],
                }
            }
        }

    def get_text(self, url: str) -> str:
        code = "P" if url.endswith("one.xml") else "A"
        return f"""
        <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>0</isOfficer></reportingOwnerRelationship>
        <nonDerivativeTransaction>
          <transactionDate><value>2026-11-18</value></transactionDate>
          <transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
        </nonDerivativeTransaction>
        """


def test_audit_issuer_filters_forms_and_finds_code_p() -> None:
    result = audit_issuer(
        cik="22701",
        start_date=date(2026, 11, 1),
        through_date=date(2026, 11, 21),
        client=StubClient(),
    )

    assert result["form4_filings_found"] == 2
    assert result["complete"] is True
    assert len(result["officer_or_director_code_p_purchases"]) == 1
    assert result["officer_or_director_code_p_purchases"][0]["transaction_code"] == "P"
