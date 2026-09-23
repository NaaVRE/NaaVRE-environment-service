import os

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
import pytest

from app.dependencies import load_config
from app.main import app

INVALID_TOKEN = 'invalid-token'
VALID_TOKEN = 'test-token'
OTHER_VALID_TOKEN = 'other-test-token'


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Ensure load_config cache is cleared between tests."""
    load_config.cache_clear()
    yield
    load_config.cache_clear()


class ConfigurableClientMixin:
    conf_filename: str
    _client: TestClient

    @pytest.fixture(autouse=True)
    def setup_client(self, monkeypatch: MonkeyPatch):
        conf_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../configurations",
                self.conf_filename,
                )
            )
        monkeypatch.setenv("CONFIG_FILE_PATH", str(conf_path))
        load_config.cache_clear()
        self._client = TestClient(app)

    @property
    def client(self) -> TestClient:
        return self._client


class TestAuthNoUsers(ConfigurableClientMixin):
    conf_filename = 'no-user.json'

    def test_no_token(self):
        resp = self.client.get("/me")
        assert resp.status_code == 401

    def test_invalid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
            )
        assert resp.status_code == 403


class TestAuthNoTokens(ConfigurableClientMixin):
    conf_filename = 'no-token.json'

    def test_no_token(self):
        resp = self.client.get("/me")
        assert resp.status_code == 401

    def test_invalid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
            )
        assert resp.status_code == 403


class TestAuthOneToken(ConfigurableClientMixin):
    conf_filename = 'one-token.json'

    def test_no_token(self):
        resp = self.client.get("/me")
        assert resp.status_code == 401

    def test_invalid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
            )
        assert resp.status_code == 403

    def test_valid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
            )
        assert resp.status_code == 200


class TestAuthMultipleTokens(ConfigurableClientMixin):
    conf_filename = 'multiple-tokens.json'

    def test_no_token(self):
        resp = self.client.get("/me")
        assert resp.status_code == 401

    def test_invalid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {INVALID_TOKEN}"}
            )
        assert resp.status_code == 403

    def test_valid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
            )
        assert resp.status_code == 200

    def test_other_valid_token(self):
        resp = self.client.get(
            "/me", headers={"Authorization": f"Bearer {OTHER_VALID_TOKEN}"}
            )
        assert resp.status_code == 200
