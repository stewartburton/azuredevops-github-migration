"""Tests for unified configuration module."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch
from azuredevops_github_migration.config import (
    load_env_file,
    substitute_env_vars,
    load_config,
    validate_config,
    detect_unresolved_placeholders,
)


class TestLoadEnvFile:
    def test_loads_env_vars(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('TEST_KEY_CFG_123=hello_world\nTEST_KEY_CFG_456="quoted_val"\n')
        with patch.dict(os.environ, {}, clear=False):
            load_env_file(str(env_file))
            assert os.environ.get("TEST_KEY_CFG_123") == "hello_world"
            assert os.environ.get("TEST_KEY_CFG_456") == "quoted_val"
        os.environ.pop("TEST_KEY_CFG_123", None)
        os.environ.pop("TEST_KEY_CFG_456", None)

    def test_skips_comments_and_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY_CFG_X=val\n")
        with patch.dict(os.environ, {}, clear=False):
            load_env_file(str(env_file))
            assert os.environ.get("KEY_CFG_X") == "val"
        os.environ.pop("KEY_CFG_X", None)

    def test_does_not_overwrite_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_CFG_VAR=new\n")
        with patch.dict(os.environ, {"EXISTING_CFG_VAR": "original"}, clear=False):
            load_env_file(str(env_file))
            assert os.environ["EXISTING_CFG_VAR"] == "original"

    def test_missing_file_no_error(self):
        load_env_file("/nonexistent/.env")


class TestSubstituteEnvVars:
    def test_simple_string(self):
        with patch.dict(os.environ, {"MY_CFG_VAR": "resolved"}):
            assert substitute_env_vars("${MY_CFG_VAR}") == "resolved"

    def test_missing_var_returns_placeholder(self):
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("${MISSING_CFG_VAR}")
            assert result == "[PLACEHOLDER_MISSING_CFG_VAR]"

    def test_nested_dict(self):
        with patch.dict(os.environ, {"TOKEN_CFG": "abc123"}):
            config = {"section": {"key": "${TOKEN_CFG}", "other": "plain"}}
            result = substitute_env_vars(config)
            assert result["section"]["key"] == "abc123"
            assert result["section"]["other"] == "plain"

    def test_list_values(self):
        with patch.dict(os.environ, {"V_CFG": "x"}):
            assert substitute_env_vars(["${V_CFG}", "literal"]) == ["x", "literal"]

    def test_non_string_passthrough(self):
        assert substitute_env_vars(42) == 42
        assert substitute_env_vars(True) is True
        assert substitute_env_vars(None) is None


class TestDetectUnresolved:
    def test_finds_placeholders(self):
        config = {"a": "[PLACEHOLDER_FOO]", "b": {"c": "[PLACEHOLDER_BAR]"}}
        result = detect_unresolved_placeholders(config)
        assert result == {"FOO", "BAR"}

    def test_clean_config(self):
        config = {"a": "real_value", "b": 123}
        assert detect_unresolved_placeholders(config) == set()


class TestValidateConfig:
    def test_valid_config(self):
        config = {
            "azure_devops": {"organization": "org", "personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        errors = validate_config(config)
        assert errors == []

    def test_missing_ado_org(self):
        config = {
            "azure_devops": {"personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        errors = validate_config(config)
        assert any("organization" in e for e in errors)

    def test_missing_github_section(self):
        config = {"azure_devops": {"organization": "org", "personal_access_token": "pat"}}
        errors = validate_config(config)
        assert any("token" in e for e in errors)


class TestLoadConfig:
    def test_load_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {
            "azure_devops": {"organization": "org", "personal_access_token": "pat"},
            "github": {"token": "tok"},
        }
        config_file.write_text(json.dumps(config_data))
        result = load_config(str(config_file))
        assert result["azure_devops"]["organization"] == "org"

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")

    def test_load_invalid_json_raises(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json")
        with pytest.raises(ValueError, match="Invalid configuration"):
            load_config(str(config_file))
