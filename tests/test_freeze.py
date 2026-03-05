"""Tests for ADO repo freeze/unfreeze functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from azuredevops_github_migration.freeze import AdoRepoFreezer


class TestAdoRepoFreezerInit:
    def test_init(self):
        freezer = AdoRepoFreezer("my-org", "my-pat")
        assert freezer.organization == "my-org"
        assert freezer.GIT_SECURITY_NAMESPACE == "2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87"


class TestFreezeRepo:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_freeze_saves_acls_and_denies(self, mock_post, mock_get, freezer):
        # Mock GET: first call is _get_project_id, second call is ACL fetch
        mock_project_response = Mock()
        mock_project_response.status_code = 200
        mock_project_response.json.return_value = {"id": "project-uuid-456", "name": "MyProject"}
        mock_project_response.raise_for_status = Mock()

        mock_acl_response = Mock()
        mock_acl_response.status_code = 200
        mock_acl_response.json.return_value = {
            "value": [{"acesDictionary": {"team-id": {"allow": 4, "deny": 0}}}]
        }
        mock_acl_response.raise_for_status = Mock()

        mock_get.side_effect = [mock_project_response, mock_acl_response]

        # Mock POST for setting deny
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        result = freezer.freeze_repo("MyProject", "repo-id-123")
        assert result["success"] is True
        assert "original_acls" in result

    @patch("requests.Session.get")
    def test_freeze_handles_api_error(self, mock_get, freezer):
        mock_get.side_effect = Exception("API unreachable")
        result = freezer.freeze_repo("MyProject", "repo-id-123")
        assert result["success"] is False
        assert "error" in result


class TestUnfreezeRepo:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_unfreeze_restores_acls(self, mock_post, mock_get, freezer):
        # Mock GET for _get_project_id
        mock_project_response = Mock()
        mock_project_response.status_code = 200
        mock_project_response.json.return_value = {"id": "project-uuid-456", "name": "MyProject"}
        mock_project_response.raise_for_status = Mock()
        mock_get.return_value = mock_project_response

        # Mock POST for restoring ACEs
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        original_acls = {"value": [{"acesDictionary": {"team-id": {"allow": 4, "deny": 0}}}]}
        result = freezer.unfreeze_repo("MyProject", "repo-id-123", original_acls)
        assert result["success"] is True


class TestResolveRepoId:
    @pytest.fixture
    def freezer(self):
        return AdoRepoFreezer("test-org", "test-pat")

    @patch("requests.Session.get")
    def test_resolve_repo_id(self, mock_get, freezer):
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [{"name": "my-repo", "id": "abc-123"}, {"name": "other", "id": "def-456"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        repo_id = freezer.resolve_repo_id("MyProject", "my-repo")
        assert repo_id == "abc-123"

    @patch("requests.Session.get")
    def test_resolve_repo_id_not_found(self, mock_get, freezer):
        mock_response = Mock()
        mock_response.json.return_value = {"value": [{"name": "other", "id": "x"}]}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="not found"):
            freezer.resolve_repo_id("MyProject", "missing-repo")
