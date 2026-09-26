import os
import subprocess
import sys
from pathlib import Path

import pytest

import jwt_secret

SCRIPT = Path(__file__).resolve().parent.parent / "jwt_secret.py"
GOOD_SECRET = "3f9c2a7d1e8b4c6f0a5d9e2b7c4f1a8d"  # 32 characters


class TestJwtSecretValidation:
    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_missing_secret_is_rejected(self, value):
        assert "not set" in jwt_secret.problem(value)

    @pytest.mark.parametrize("value", [
        "changeme", "CHANGEME", " changeme ", "your_long_random_secret_here", "dev-secret",
    ])
    def test_placeholder_is_rejected(self, value):
        message = jwt_secret.problem(value)
        assert "placeholder" in message
        assert "MUST be changed" in message

    def test_short_secret_is_rejected(self):
        message = jwt_secret.problem(GOOD_SECRET[:31])
        assert "31 characters" in message
        assert "MUST be changed" in message

    @pytest.mark.parametrize("value", [None, "", "changeme", "dev-secret", GOOD_SECRET[:31]])
    def test_every_error_tells_how_to_generate_a_secret(self, value):
        assert "openssl rand -hex 32" in jwt_secret.problem(value)

    def test_random_32_character_secret_is_accepted(self):
        assert jwt_secret.problem(GOOD_SECRET) is None

    def test_load_raises_with_message(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "changeme")
        with pytest.raises(RuntimeError, match="MUST be changed"):
            jwt_secret.load()

    def test_load_returns_valid_secret(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", GOOD_SECRET)
        assert jwt_secret.load() == GOOD_SECRET


class TestEntrypointCheck:
    """entrypoint.sh runs `python jwt_secret.py` before migrations."""

    def _run(self, secret):
        env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
        if secret is not None:
            env["JWT_SECRET"] = secret
        return subprocess.run([sys.executable, str(SCRIPT)], env=env,
                              capture_output=True, text=True, timeout=30)

    def test_placeholder_exits_with_error(self):
        result = self._run("changeme")
        assert result.returncode == 1
        assert "MUST be changed" in result.stderr
        assert "openssl rand -hex 32" in result.stderr

    def test_short_secret_exits_with_error_and_fix(self):
        result = self._run(GOOD_SECRET[:20])
        assert result.returncode == 1
        assert "openssl rand -hex 32" in result.stderr

    def test_unset_exits_with_error(self):
        result = self._run(None)
        assert result.returncode == 1
        assert "not set" in result.stderr

    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_exits_with_error(self, value):
        # `JWT_SECRET=` left blank in .env reaches the container as an empty string.
        result = self._run(value)
        assert result.returncode == 1
        assert "not set" in result.stderr
        assert "openssl rand -hex 32" in result.stderr

    def test_valid_secret_exits_cleanly(self):
        result = self._run(GOOD_SECRET)
        assert result.returncode == 0
        assert result.stderr == ""
