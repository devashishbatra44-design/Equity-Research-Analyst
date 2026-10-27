"""Check that a required value exists in .env without displaying the value."""

from pathlib import Path


def read_dotenv_value(path: Path, key: str) -> str | None:
    """Read one simple KEY=value entry from a .env file.

    This small Week 1 example supports blank lines, comments, optional `export`,
    and matching single or double quotes. It does not expand shell variables.
    """
    if not path.is_file():
        raise FileNotFoundError(f"No .env file found at {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()

        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value

    return None


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        value = read_dotenv_value(env_path, "GENAI_API_KEY")
    except OSError as error:
        print(f"Setup check failed: {error}")
        return 1

    if value:
        print("GENAI_API_KEY is present. The value is hidden.")
    else:
        print("GENAI_API_KEY is blank or missing. The value was not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
