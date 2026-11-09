"""Optional, source-bounded Tavily research for the FIN 67110 desk.

Tavily results supplement the saved SEC evidence. They never replace a filing,
XBRL fact, deterministic calculation, or the mandatory final Verifier.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from dotenv import load_dotenv


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
SEARCH_DEPTHS = {"basic", "advanced"}


class TavilyResearchError(RuntimeError):
    """Raised when an explicitly requested Tavily search cannot complete."""


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TavilyResearchError(f"Expected a JSON object in {path}.")
    return value


def _clean_company_name(value: str) -> str:
    return " ".join(value.replace("/NEW", "").replace("/DE", "").split()).strip()


def build_company_query(manifest: dict[str, Any]) -> str:
    """Build one focused, company-neutral query from the saved SEC identity."""
    company = manifest.get("company", {})
    ticker = str(company.get("ticker") or manifest.get("main_ticker") or "").strip().upper()
    legal_name = _clean_company_name(str(company.get("legal_name") or ticker))
    if not ticker:
        raise TavilyResearchError("The saved manifest has no ticker for Tavily research.")
    return (
        f'"{legal_name}" {ticker} latest company developments catalysts competitive risks '
        "investor relations official sources"
    )


def _request_search(
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: int = 45,
) -> dict[str, Any]:
    request = urllib.request.Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise TavilyResearchError(f"Tavily returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TavilyResearchError(f"Tavily search failed: {exc}") from exc
    if not isinstance(result, dict):
        raise TavilyResearchError("Tavily returned a response that was not a JSON object.")
    return result


def _source_class(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host == "sec.gov" or host.endswith(".sec.gov"):
        return "primary_regulatory"
    return "supplementary_web"


def _compact_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(item.get("title") or "Untitled source").strip(),
        "url": str(item.get("url") or "").strip(),
        "published_date": item.get("published_date"),
        "score": item.get("score"),
        "content": str(item.get("content") or "").strip(),
        "source_class": _source_class(str(item.get("url") or "")),
    }


def render_tavily_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# Supplementary Tavily research",
        "",
        f"Query: `{record.get('query', '')}`",
        "",
        f"Retrieved: {record.get('retrieved_at', '')}",
        "",
        "This material is supplementary web context. SEC filings and saved XBRL facts remain authoritative for financial claims.",
        "",
        "## Sources",
        "",
    ]
    results = record.get("results", [])
    if not results:
        lines.append("No sources were returned.")
    for index, result in enumerate(results, start=1):
        title = result.get("title") or "Untitled source"
        url = result.get("url") or ""
        published = result.get("published_date") or "Date not supplied"
        lines.extend(
            [
                f"### {index}. [{title}]({url})",
                "",
                f"Published or updated: {published}.",
                "",
                str(result.get("content") or "No excerpt returned."),
                "",
            ]
        )
    lines.extend(
        [
            "## Use restrictions",
            "",
            "- Do not use a Tavily result as evidence for any of the eleven audited filing claims.",
            "- Do not use a web number unless the saved primary evidence independently confirms it.",
            "- Cite the source URL and publication date for every qualitative web claim.",
            "- Keep the final Insight line filing-bounded so the course Verifier can reproduce it.",
        ]
    )
    return "\n".join(lines) + "\n"


def research_run_folder(
    run_folder: Path,
    repository_root: Path,
    *,
    search_depth: str = "advanced",
    max_results: int = 5,
    requester: Callable[[dict[str, Any], dict[str, str]], dict[str, Any]] | None = None,
) -> Path:
    """Run one Tavily search and save a provenance-preserving sidecar."""
    if search_depth not in SEARCH_DEPTHS:
        raise TavilyResearchError(f"search_depth must be one of {sorted(SEARCH_DEPTHS)}.")
    if not 1 <= max_results <= 5:
        raise TavilyResearchError("max_results must be between 1 and 5 for this course integration.")

    load_dotenv(repository_root / ".env", override=False)
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    auth_mode = "api_key" if api_key else "keyless"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FIN67110-equity-research-desk/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["X-Tavily-Access-Mode"] = "keyless"

    manifest = _load_json(run_folder / "manifest.json")
    query = build_company_query(manifest)
    payload = {
        "query": query,
        "topic": "finance",
        "search_depth": search_depth,
        "chunks_per_source": 3,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_published_date": True,
    }
    raw = (requester or _request_search)(payload, headers)
    raw_results = raw.get("results", [])
    if not isinstance(raw_results, list):
        raise TavilyResearchError("Tavily returned a results field that was not a list.")
    results = [_compact_result(item) for item in raw_results if isinstance(item, dict) and item.get("url")]
    record = {
        "provider": "Tavily Search API",
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "auth_mode": auth_mode,
        "query": query,
        "request": payload,
        "request_id": raw.get("request_id"),
        "response_time_seconds": raw.get("response_time"),
        "result_count": len(results),
        "results": results,
        "course_boundary": {
            "supplementary_context_only": True,
            "sec_remains_authoritative": True,
            "core_financial_claims_allowed": False,
            "numbers_require_primary_source_confirmation": True,
            "recommendation_may_not_rely_on_tavily_alone": True,
            "verifier_remains_final_node": True,
        },
    }
    output_path = run_folder / "tavily_research.json"
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_folder / "tavily_research.md").write_text(render_tavily_markdown(record), encoding="utf-8")

    manifest["tavily_research"] = {
        "enabled": True,
        "provider": "Tavily Search API",
        "auth_mode": auth_mode,
        "query_count": 1,
        "search_depth": search_depth,
        "result_count": len(results),
        "json": output_path.name,
        "markdown": "tavily_research.md",
        "supplementary_only": True,
    }
    manifest["output_filenames"] = sorted(
        set(manifest.get("output_filenames", [])) | {output_path.name, "tavily_research.md"}
    )
    (run_folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def role_context(record: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded Tavily context sent only to the Research Analyst."""
    return {
        "provider": record.get("provider"),
        "retrieved_at": record.get("retrieved_at"),
        "query": record.get("query"),
        "results": record.get("results", []),
        "rules": [
            "Use these results only for qualitative recent developments, catalysts, or competitive risks.",
            "Put each web claim in a subsection titled Supplementary web context.",
            "Cite the source as a Markdown link and state its publication date when supplied.",
            "Do not use a web number unless saved primary evidence independently confirms it.",
            "Do not use Tavily evidence in the final Insight line.",
            "Do not use Tavily as evidence for an audited filing claim or recommendation by itself.",
        ],
        "course_boundary": record.get("course_boundary", {}),
    }
