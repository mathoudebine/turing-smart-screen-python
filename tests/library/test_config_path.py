import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

from library.config_path import CONFIG_FILE_ENV_VAR, ConfigPathError, resolve_config_path


class TestResolveConfigPath(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.default = self.tmp / "default_config.yaml"
        self.default.write_text("config: {}\n", encoding="utf-8")
        self.option_file = self.tmp / "option.yaml"
        self.option_file.write_text("config: {}\n", encoding="utf-8")
        self.env_file = self.tmp / "env.yaml"
        self.env_file.write_text("config: {}\n", encoding="utf-8")

    def resolve(self, argv, env=None):
        return resolve_config_path(["prog"] + argv, env or {}, self.default)

    def test_default_when_nothing_selected(self):
        self.assertEqual(self.resolve([]), self.default)

    def test_default_rejected_when_missing(self):
        with self.assertRaises(ConfigPathError) as ctx:
            resolve_config_path(["prog"], {}, self.tmp / "absent.yaml")
        self.assertIn("absent.yaml", str(ctx.exception))

    def test_long_option(self):
        self.assertEqual(self.resolve(["--config", str(self.option_file)]), self.option_file)

    def test_long_option_equals_form(self):
        self.assertEqual(self.resolve([f"--config={self.option_file}"]), self.option_file)

    def test_short_option(self):
        self.assertEqual(self.resolve(["-c", str(self.option_file)]), self.option_file)

    def test_option_wins_over_env(self):
        env = {CONFIG_FILE_ENV_VAR: str(self.env_file)}
        self.assertEqual(self.resolve(["--config", str(self.option_file)], env), self.option_file)

    def test_env_used_without_option(self):
        env = {CONFIG_FILE_ENV_VAR: str(self.env_file)}
        self.assertEqual(self.resolve([], env), self.env_file)

    def test_empty_env_falls_back_to_default(self):
        self.assertEqual(self.resolve([], {CONFIG_FILE_ENV_VAR: "   "}), self.default)

    def test_after_double_dash_option_ignored(self):
        self.assertEqual(self.resolve(["--", "--config", str(self.option_file)]), self.default)

    def test_missing_file_rejected(self):
        with self.assertRaises(ConfigPathError) as ctx:
            self.resolve(["--config", str(self.tmp / "nope.yaml")])
        self.assertIn("nope.yaml", str(ctx.exception))

    def test_directory_rejected(self):
        with self.assertRaises(ConfigPathError) as ctx:
            self.resolve(["--config", str(self.tmp)])
        self.assertIn("directory", str(ctx.exception))

    def test_option_without_value_rejected(self):
        with self.assertRaises(ConfigPathError):
            self.resolve(["--config"])

    def test_empty_equals_value_rejected(self):
        with self.assertRaises(ConfigPathError):
            self.resolve(["--config="])

    def test_tilde_expanded(self):
        with mock.patch.dict("os.environ", {"HOME": str(self.tmp)}):
            self.assertEqual(
                self.resolve(["--config", "~/option.yaml"]),
                self.option_file,
            )


if __name__ == "__main__":
    unittest.main()
