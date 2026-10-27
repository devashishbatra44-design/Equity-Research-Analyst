import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from env_check import read_dotenv_value


class DotenvReadTest(unittest.TestCase):
    def test_reads_fake_value_without_printing_it(self) -> None:
        fake_secret = "week1-demo-not-a-real-key"
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                f"# comment\nGENAI_API_KEY='{fake_secret}'\n", encoding="utf-8"
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                value = read_dotenv_value(env_path, "GENAI_API_KEY")

        self.assertEqual(value, fake_secret)
        self.assertNotIn(fake_secret, output.getvalue())

    def test_returns_none_for_blank_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("GENAI_API_KEY=\n", encoding="utf-8")
            self.assertEqual(read_dotenv_value(env_path, "GENAI_API_KEY"), "")


if __name__ == "__main__":
    unittest.main()
