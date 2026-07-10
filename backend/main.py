from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dashboard import build_dashboard_overview, build_dashboard_report

app = FastAPI(
    title="AQuantAI",
    version="0.2.0",
    description="A-share AI multi-factor quantitative research platform with a local read-only Dashboard.",
)

DASHBOARD_STATIC_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "static"
app.mount("/dashboard/static", StaticFiles(directory=DASHBOARD_STATIC_DIR), name="dashboard-static")


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
