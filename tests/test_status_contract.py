"""Gate tasks/status.md against the shared status contract validator.

The validator lives in the AIKB vault, not this repo (contract §9.1: each
project wires the shared checker into its own gate rather than vendoring a
copy). If the vault isn't mounted at any known path, skip rather than fail --
that's an environment gap, not a status.md defect.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_CANDIDATE_PATHS = [
    Path("/mnt/e/KnowledgeBase/AIKB/scripts/status_contract.py"),
    Path("E:/KnowledgeBase/AIKB/scripts/status_contract.py"),
]


def _load_status_contract():
    for candidate in _CANDIDATE_PATHS:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("status_contract", candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    return None


def test_status_md_passes_shape_contract():
    status_contract = _load_status_contract()
    if status_contract is None:
        pytest.skip("AIKB vault not mounted; shared status_contract.py unavailable")

    status_path = Path(__file__).resolve().parent.parent / "tasks" / "status.md"
    result = status_contract.validate(status_path, mode="shape")

    assert result.green, "\n".join(
        f"line {f.line}: class {f.class_} {f.category}/{f.branch}: {f.subject}"
        for f in result.findings
    )
