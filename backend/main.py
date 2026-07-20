from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.evidence_intelligence import router as evidence_intelligence_router
from backend.api.industry_alpha import router as industry_alpha_router
from backend.api.market_cockpit import router as market_cockpit_router
from dashboard import build_dashboard_overview, build_dashboard_report

app = FastAPI(
    title="AQuantAI",
    version="0.2.0",
    description="A-share AI multi-factor quantitative research platform with a local read-only Dashboard.",
)

DASHBOARD_STATIC_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "static"
MARKET_COCKPIT_STATIC_DIR = Path(__file__).resolve().parents[1] / "market_cockpit" / "static"
EVIDENCE_INTELLIGENCE_STATIC_DIR = (
    Path(__file__).resolve().parents[1] / "evidence_intelligence" / "static"
)
app.mount("/dashboard/static", StaticFiles(directory=DASHBOARD_STATIC_DIR), name="dashboard-static")
app.mount(
    "/market-cockpit/static",
    StaticFiles(directory=MARKET_COCKPIT_STATIC_DIR),
    name="market-cockpit-static",
)
app.mount(
    "/evidence-intelligence/static",
    StaticFiles(directory=EVIDENCE_INTELLIGENCE_STATIC_DIR),
    name="evidence-intelligence-static",
)
app.include_router(market_cockpit_router)
app.include_router(industry_alpha_router)
app.include_router(evidence_intelligence_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "project": "AQuantAI",
        "status": "v0.2 research-only local Dashboard baseline",
        "version": "0.2.0",
        "phase": "v0.2 local read-only Dashboard baseline",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> FileResponse:
    """Serve the local, read-only Dashboard presentation page."""
    return FileResponse(DASHBOARD_STATIC_DIR / "dashboard.html", media_type="text/html")


@app.get("/dashboard/overview")
def dashboard_overview() -> dict:
    return build_dashboard_overview().to_dict()


@app.get("/dashboard/report")
def dashboard_report() -> dict:
    return build_dashboard_report().to_dict()


@app.get("/market-cockpit", include_in_schema=False)
def market_cockpit_page() -> FileResponse:
    """Serve the read-only database-backed Market Cockpit page."""
    return FileResponse(
        MARKET_COCKPIT_STATIC_DIR / "market_cockpit.html",
        media_type="text/html",
    )


@app.get("/evidence-intelligence", include_in_schema=False)
def evidence_intelligence_page() -> FileResponse:
    """Serve the read-only Evidence Intelligence research-change page."""
    return FileResponse(
        EVIDENCE_INTELLIGENCE_STATIC_DIR / "evidence_intelligence.html",
        media_type="text/html",
    )
