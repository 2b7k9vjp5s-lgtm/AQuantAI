from __future__ import annotations

from threading import Event, Thread
from uuid import UUID

from industry_alpha.stage2_revision_locks import revision_lock


IDENTITY = UUID("12345678-1234-5678-1234-567812345678")


def test_revision_lock_returns_same_object_for_same_key() -> None:
    assert revision_lock("research", IDENTITY) is revision_lock("research", IDENTITY)


def test_revision_lock_isolates_different_keys() -> None:
    other_identity = UUID("87654321-4321-8765-4321-876543218765")

    assert revision_lock("research", IDENTITY) is not revision_lock(
        "hypothesis", IDENTITY
    )
    assert revision_lock("research", IDENTITY) is not revision_lock(
        "research", other_identity
    )


def test_revision_lock_is_reentrant() -> None:
    lock = revision_lock("expectation", IDENTITY)

    with lock:
        assert lock.acquire(blocking=False)
        lock.release()


def test_revision_lock_excludes_second_thread_for_same_key() -> None:
    first_entered = Event()
    release_first = Event()
    second_waiting = Event()
    second_entered = Event()

    def hold_lock() -> None:
        with revision_lock("valuation", IDENTITY):
            first_entered.set()
            release_first.wait()

    def wait_for_lock() -> None:
        second_waiting.set()
        with revision_lock("valuation", IDENTITY):
            second_entered.set()

    first = Thread(target=hold_lock, daemon=True)
    second = Thread(target=wait_for_lock, daemon=True)
    first.start()
    second_started = False

    try:
        assert first_entered.wait(timeout=5)
        second.start()
        second_started = True
        assert second_waiting.wait(timeout=5)
        assert not second_entered.wait(timeout=0.1)
    finally:
        release_first.set()
        first.join(timeout=5)
        if second_started:
            second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert second_entered.is_set()
