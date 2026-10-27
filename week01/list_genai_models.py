"""List models available to this account without displaying the API key."""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from env_check import read_dotenv_value


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    api_key = read_dotenv_value(env_path, "GENAI_API_KEY")
    base_url = read_dotenv_value(env_path, "GENAI_BASE_URL")

    if not api_key:
        print("GENAI_API_KEY is blank or missing in .env.")
        return 1
    if not base_url:
        print("GENAI_BASE_URL is blank or missing in .env.")
        return 1

    request = Request(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        print(f"Model-list request failed with HTTP {error.code}.")
        return 1
    except (TimeoutError, URLError):
        print("Could not reach GenAI Studio. Check network access and try again.")
        return 1

    models = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = [model.get("id") for model in models if isinstance(model, dict)]
    model_ids = [model_id for model_id in model_ids if model_id]
    if not model_ids:
        print("The API returned no model IDs in the expected format.")
        return 1

    print("Models available to this API key:")
    for model_id in model_ids:
        print(f"- {model_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
