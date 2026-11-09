from __future__ import annotations

import json
from pathlib import Path

import equity_research_crewai.main as main
from equity_research_crewai.tavily_research import research_run_folder, role_context
from equity_research_crewai.verifier import build_semantic_payload, VerificationMark


def _saved_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    manifest = {
        "run_status": "success",
        "main_ticker": "TEST",
        "company": {"ticker": "TEST", "legal_name": "TEST COMPANY /NEW"},
        "output_filenames": ["manifest.json"],
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run


def _response() -> dict[str, object]:
    return {
        "request_id": "test-request",
        "response_time": 0.5,
        "results": [
            {
                "title": "Test Company investor update",
                "url": "https://investor.example.com/update",
                "published_date": "2026-11-07",
                "score": 0.9,
                "content": "The company described a new operating initiative.",
            }
        ],
    }


def test_keyless_search_saves_provenance_and_never_a_secret(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    run = _saved_run(tmp_path)

    def fake_request(payload: dict, headers: dict) -> dict:
        assert payload["topic"] == "finance"
        assert payload["search_depth"] == "advanced"
        assert payload["max_results"] == 5
        assert payload["include_answer"] is False
        assert headers["X-Tavily-Access-Mode"] == "keyless"
        assert "Authorization" not in headers
        return _response()

    output = research_run_folder(run, tmp_path, requester=fake_request)
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["auth_mode"] == "keyless"
    assert record["result_count"] == 1
    assert record["course_boundary"]["sec_remains_authoritative"] is True
    assert "TAVILY_API_KEY" not in output.read_text(encoding="utf-8")
    assert (run / "tavily_research.md").exists()


def test_api_key_is_used_only_in_request_header(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-secret")
    run = _saved_run(tmp_path)

    def fake_request(payload: dict, headers: dict) -> dict:
        assert headers["Authorization"] == "Bearer tvly-test-secret"
        assert "X-Tavily-Access-Mode" not in headers
        return _response()

    output = research_run_folder(run, tmp_path, search_depth="basic", requester=fake_request)
    saved = output.read_text(encoding="utf-8")
    assert "tvly-test-secret" not in saved
    assert json.loads(saved)["auth_mode"] == "api_key"


def test_research_analyst_receives_bounded_tavily_context(tmp_path: Path) -> None:
    record = {
        "provider": "Tavily Search API",
        "retrieved_at": "2026-11-08T00:00:00-05:00",
        "query": "test query",
        "results": _response()["results"],
        "course_boundary": {"supplementary_context_only": True},
    }
    bounded = role_context(record)
    assert "Do not use Tavily evidence in the final Insight line." in bounded["rules"]

    context = {
        "business_and_mda_source_text": {},
        "company": {},
        "earnings_release_source_text": {},
        "filings": {},
        "faskills_methodology": {},
        "tavily_research": record,
    }
    handoff = json.loads(main._research_handoff(context))
    assert "supplementary_tavily_research" not in handoff["context"]
    assert "course_operating_rules" in handoff["context"]


def test_verifier_receives_only_cited_saved_tavily_results(tmp_path: Path) -> None:
    run = _saved_run(tmp_path)
    (run / "facts.json").write_text(
        json.dumps({"reference_fiscal_year": "2026", "concepts": {}, "earnings_release_extraction": {}}),
        encoding="utf-8",
    )
    tavily_record = {
        "query": "test query",
        "retrieved_at": "2026-11-08T00:00:00-05:00",
        "results": _response()["results"],
        "course_boundary": {"supplementary_context_only": True},
    }
    (run / "tavily_research.json").write_text(json.dumps(tavily_record), encoding="utf-8")
    report = "A qualitative update was reported. [Source](https://investor.example.com/update)"
    mark = VerificationMark("claim", "x", "x", "Correct", "evidence")
    payload = build_semantic_payload(run, report, [mark])
    cited = payload["supplemental_tavily_research"]["cited_results"]
    assert len(cited) == 1
    assert cited[0]["filing_evidence"] is False


def test_cli_exposes_optional_tavily_without_a_verifier_bypass() -> None:
    destinations = {action.dest for action in main.build_parser()._actions}
    assert {"tavily", "tavily_depth", "reuse_tavily"} <= destinations
    assert not any("disable" in name or "skip" in name for name in destinations)
