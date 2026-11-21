from equity_research_crewai.sec_form4_audit import parse_form4


def test_form4_parser_keeps_code_date_and_owner_roles() -> None:
    xml = """
    <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>0</isOfficer></reportingOwnerRelationship>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-04-02</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
    </nonDerivativeTransaction>
    """
    assert parse_form4(xml) == (
        {
            "transaction_date": "2026-04-02",
            "transaction_code": "P",
            "is_director": True,
            "is_officer": False,
        },
    )
