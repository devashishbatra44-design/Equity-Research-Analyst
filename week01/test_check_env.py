import tempfile
import unittest
from pathlib import Path

from check_env import format_result, read_dotenv


class CheckEnvTest(unittest.TestCase):
    def test_reads_dotenv_and_masks_key_to_four_characters(self) -> None:
        fake_key = "fake-demo-value-not-a-real-key"
        user_agent = "Test Student test@example.edu"
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                f"GENAI_API_KEY='{fake_key}'\nSEC_USER_AGENT=\"{user_agent}\"\n",
                encoding="utf-8",
            )
            values = read_dotenv(env_path)

        output = format_result(values["GENAI_API_KEY"], values["SEC_USER_AGENT"])
        self.assertEqual(output, f"{fake_key[:4]}...\n{user_agent}")
        self.assertNotIn(fake_key, output)


if __name__ == "__main__":
    unittest.main()
