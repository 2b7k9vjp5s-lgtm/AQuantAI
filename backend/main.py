from fastapi import FastAPI

from dashboard import build_dashboard_overview, build_dashboard_report

app = FastAPI(
    title="AQuantAI",
    version="0.1.0",
    description="A-share AI multi-factor quantitative research platform.",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "project": "AQuantAI",
        "status": "v0.1 research-only baseline",
        "version": "0.1.0",
        "phase": "v0.1 baseline freeze",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard/overview")
def dashboard_overview() -> dict:
    return build_dashboard_overview().to_dict()


@app.get("/dashboard/report")
def dashboard_report() -> dict:
    return build_dashboard_report().to_dict()
