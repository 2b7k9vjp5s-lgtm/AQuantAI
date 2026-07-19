from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from industry_alpha.errors import EvidenceLedgerConflictError
from industry_alpha.stage2_integrity import translate_integrity


def test_translate_integrity_allows_success() -> None:
    completed = False

    with translate_integrity("unused conflict message"):
        completed = True

    assert completed


def test_translate_integrity_preserves_exact_message_and_cause() -> None:
    original = IntegrityError("INSERT", {}, RuntimeError("duplicate"))

    with pytest.raises(EvidenceLedgerConflictError) as caught:
        with translate_integrity("exact Stage 2 conflict message"):
            raise original

    assert str(caught.value) == "exact Stage 2 conflict message"
    assert caught.value.__cause__ is original


def test_translate_integrity_passes_through_same_non_integrity_exception() -> None:
    original = RuntimeError("not an integrity failure")

    with pytest.raises(RuntimeError) as caught:
        with translate_integrity("must not be used"):
            raise original

    assert caught.value is original
