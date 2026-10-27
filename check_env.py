"""Lab 01 check: read local credentials without changing or uploading .env."""

from pathlib import Path


def read_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=value entries without expanding shell expressions."""
    if not path.is_file():
        raise FileNotFoundError(f"No .env file found at {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()

        name, separator, value = line.partition("=")
        if not separator:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    return values


def format_result(api_key: str, user_agent: str) -> str:
    """Return the two lab lines, with only the requested key prefix shown."""
    return f"{api_key[:4]}...\n{user_agent}"


def main() -> int:
    env_path = Path(__file__).resolve().parent / ".env"
    try:
        values = read_dotenv(env_path)
    except OSError as error:
        print(f"Setup check failed: {error}")
        return 1

    # Keep the project's existing variable name. API_KEY is accepted too.
    api_key = values.get("API_KEY") or values.get("GENAI_API_KEY", "")
    user_agent = values.get("SEC_USER_AGENT", "")
    if not api_key or api_key == "paste-here":
        print("API_KEY is blank or missing. The key value was not displayed.")
        return 1
    if not user_agent:
        print("SEC_USER_AGENT is blank or missing.")
        return 1

    # Lab 01 asks for this masked prefix. Run only in the local terminal.
    print(format_result(api_key, user_agent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
