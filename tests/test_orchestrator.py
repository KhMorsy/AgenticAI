"""Tests for orchestrator module (if it exists)."""

import importlib

import pytest


class TestOrchestratorAvailability:
    """Verify that the orchestrator module can be discovered and has the expected entry point."""

    def test_orchestrator_entry_point_is_configured(self):
        """pyproject.toml declares agentic-orchestrator = src.orchestrator.server:main"""
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml not found")
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        scripts = data.get("project", {}).get("scripts", {})
        assert "agentic-orchestrator" in scripts

    def test_orchestrator_server_module_importable(self):
        """Try importing the orchestrator server module."""
        try:
            mod = importlib.import_module("src.orchestrator.server")
            assert hasattr(mod, "main"), "orchestrator server module should expose a main() function"
        except ModuleNotFoundError:
            pytest.skip("src.orchestrator.server module not yet created")

    def test_orchestrator_coordinator_importable(self):
        """Try importing a coordinator module."""
        try:
            mod = importlib.import_module("src.orchestrator.coordinator")
            assert mod is not None
        except ModuleNotFoundError:
            pytest.skip("src.orchestrator.coordinator module not yet created")
