from unittest import mock

import pytest

from azuredevops_github_migration.migrate import AzureDevOpsClient, MigrationError


class DummyResp:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        from requests import HTTPError

        raise HTTPError(
            f"{self.status_code} Client Error: Unauthorized for url", response=self
        )


def test_get_projects_401_guidance(monkeypatch):
    client = AzureDevOpsClient("fake-org", "FAKEPAT123")

    def fake_get(url, timeout):
        class E(Exception):
            pass

        return DummyResp(401)

    monkeypatch.setattr(client.session, "get", fake_get)
    with pytest.raises(MigrationError) as exc:
        client.get_projects()
    msg = str(exc.value)
    assert "401" in msg
    assert "PAT validity" in msg or "Authentication failed" in msg
    assert "curl -u" in msg
