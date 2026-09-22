"""Structural smoke test: src modules parse and expose their public API.

Deps (pandas etc.) are not installed in this environment, so this test checks
structure only via the AST.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).parent.parent
MODULES = [
    ROOT / "src" / "extractors" / "base.py",
    ROOT / "src" / "transformers" / "base.py",
]


def test_modules_parse():
    for mod in MODULES:
        ast.parse(mod.read_text(encoding="utf-8"), filename=str(mod))


def test_expected_classes_present():
    expected = {
        "base.py": {"BaseExtractor", "DatabaseExtractor", "APIExtractor",
                    "FileExtractor", "ExtractionResult"},
    }
    trans = ast.parse((ROOT / "src" / "transformers" / "base.py").read_text())
    names = {n.name for n in ast.walk(trans) if isinstance(n, ast.ClassDef)}
    assert {"BaseTransformer", "CleaningTransformer", "ValidationTransformer",
            "EnrichmentTransformer", "Pipeline"} <= names
    ext = ast.parse((ROOT / "src" / "extractors" / "base.py").read_text())
    names = {n.name for n in ast.walk(ext) if isinstance(n, ast.ClassDef)}
    assert expected["base.py"] <= names
