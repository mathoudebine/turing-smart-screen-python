import importlib.util
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 60
FULL_RUNTIME = importlib.util.find_spec("GPUtil") is not None


def _make_simu_config(dest: Path, theme: str = "3.5inchTheme2") -> Path:
    # Start from the shipped schema and switch to simulated display + stub sensors
    with open(REPO_ROOT / "config.yaml", "rt", encoding="utf8") as stream:
        data = yaml.safe_load(stream)
    data["display"]["REVISION"] = "SIMU"
    data["config"]["THEME"] = theme
    data["config"]["HW_SENSORS"] = "STUB"
    dest.write_text(yaml.safe_dump(data), encoding="utf-8")
    return dest


def _run(args, env=None, cwd=None):
    full_env = dict(os.environ)
    full_env.pop("TURING_CONFIG_FILE", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True, text=True, timeout=TIMEOUT,
        env=full_env, cwd=str(cwd or REPO_ROOT),
    )


def _run_monitor_until_frame(config_args, screencap_dir: Path, extra_env=None):
    # Launch main.py with SIMU config, wait until the simulated screen produced
    # a frame, then terminate it. Returns the screencap path.
    proc = subprocess.Popen(
        [sys.executable, "main.py", *config_args],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env={**{k: v for k, v in os.environ.items() if k != "TURING_CONFIG_FILE"}, **(extra_env or {})},
        cwd=str(REPO_ROOT),
    )
    screencap = REPO_ROOT / "screencap.png"
    screencap.unlink(missing_ok=True)
    deadline = time.monotonic() + TIMEOUT
    try:
        while time.monotonic() < deadline:
            if screencap.exists():
                break
            if proc.poll() is not None:
                raise AssertionError(f"main.py exited early ({proc.returncode}):\n{proc.stdout.read()}")
            time.sleep(0.5)
        else:
            raise AssertionError("main.py did not render a SIMU frame in time")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)
    if not screencap_dir.exists():
        screencap_dir.mkdir(parents=True)
    shutil.move(str(screencap), str(screencap_dir / "screencap.png"))
    return screencap_dir / "screencap.png"


class TestConfigFileSelectionCli(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def test_main_missing_config_file_exits_1(self):
        res = _run(["main.py", "--config", str(self.tmp / "absent.yaml")])
        self.assertEqual(res.returncode, 1)
        self.assertIn("does not exist", res.stdout + res.stderr)

    def test_main_broken_yaml_exits_1(self):
        broken = self.tmp / "broken.yaml"
        broken.write_text("\t: [unclosed\n", encoding="utf-8")
        res = _run(["main.py", "--config", str(broken)])
        self.assertEqual(res.returncode, 1)
        self.assertIn("Cannot load configuration file", res.stdout + res.stderr)

    def test_theme_editor_requires_theme_argument(self):
        res = _run(["theme-editor.py"])
        self.assertEqual(res.returncode, 2)
        self.assertIn("theme", res.stderr)

    def test_theme_editor_missing_config_file_exits_1(self):
        res = _run(["theme-editor.py", "3.5inchTheme2", "--config", str(self.tmp / "absent.yaml")])
        self.assertEqual(res.returncode, 1)
        self.assertIn("does not exist", res.stdout + res.stderr)

    @unittest.skipUnless(FULL_RUNTIME, "main.py SIMU run needs the full runtime dependencies")
    def test_main_uses_config_from_option(self):
        config = _make_simu_config(self.tmp / "custom.yaml")
        frame = _run_monitor_until_frame(["--config", str(config)], self.tmp / "opt")
        self.assertTrue(frame.exists())
        # The user config.yaml in the repo must stay untouched
        with open(REPO_ROOT / "config.yaml", "rt", encoding="utf8") as stream:
            self.assertNotEqual(yaml.safe_load(stream)["display"]["REVISION"], "SIMU")

    @unittest.skipUnless(FULL_RUNTIME, "main.py SIMU run needs the full runtime dependencies")
    def test_main_uses_config_from_env(self):
        config = _make_simu_config(self.tmp / "env.yaml")
        frame = _run_monitor_until_frame([], self.tmp / "env", extra_env={"TURING_CONFIG_FILE": str(config)})
        self.assertTrue(frame.exists())


if __name__ == "__main__":
    unittest.main()
