"""Send a minimal, non-sensitive request to Purdue GenAI Studio."""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from env_check import read_dotenv_value


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    api_key = read_dotenv_value(env_path, "GENAI_API_KEY")
    base_url = read_dotenv_value(env_path, "GENAI_BASE_URL")
    model = read_dotenv_value(env_path, "GENAI_MODEL")
    if not api_key or not base_url or not model:
        print("Set GENAI_API_KEY, GENAI_BASE_URL, and GENAI_MODEL in .env first.")
        return 1

    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply exactly READY."}],
            "stream": False,
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.load(response)
    except HTTPError as error:
        print(f"GenAI Studio request failed with HTTP {error.code}.")
        return 1
    except (TimeoutError, URLError):
        print("Could not reach GenAI Studio. Check network access and try again.")
        return 1

    choices = payload.get("choices", []) if isinstance(payload, dict) else []
    content = choices[0].get("message", {}).get("content") if choices else None
    if not content:
        print("The API returned no assistant text in the expected format.")
        return 1

    print(f"API request succeeded with model {model}.")
    print(f"Model response: {content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
