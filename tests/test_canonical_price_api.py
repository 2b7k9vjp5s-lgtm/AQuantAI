from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.canonical_price import get_canonical_price_session_factory
from backend.database.models import Base
from backend.main import app


def test_routes_require_both_as_of_boundaries_and_are_get_only():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    app.dependency_overrides[get_canonical_price_session_factory] = lambda: factory
    try:
        with TestClient(app) as client:
            identity = "00000000-0000-0000-0000-000000000001"
            assert client.get(f"/market-data/listed-instruments/{identity}").status_code == 422
            response = client.get(f"/market-data/listed-instruments/{identity}?as_of_cutoff=2026-07-22&as_of_recorded_at_utc=2026-07-22T10:00:00Z")
            assert response.status_code == 404
            assert client.post(f"/market-data/listed-instruments/{identity}").status_code == 405
            assert client.get(f"/market-data/canonical-prices/{identity}?as_of_cutoff=2026-07-22&as_of_recorded_at_utc=2026-07-22T12:00:00%2B02:00").status_code == 422
            assert client.get(f"/market-data/canonical-prices/{identity}?as_of_cutoff=2026-07-23&as_of_recorded_at_utc=2026-07-22T12:00:00Z").status_code == 422
    finally:
        app.dependency_overrides.clear(); engine.dispose()
