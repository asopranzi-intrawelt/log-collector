"""Rende importabili gli script di bin/, compresi quelli con il trattino nel nome."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(BIN))


def load_script(filename: str):
    """Carica uno script di bin/ come modulo, dato il nome del file."""
    name = filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, BIN / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def params_text() -> str:
    return (FIXTURES / "parametri-completi.yaml").read_text(encoding="utf-8")
