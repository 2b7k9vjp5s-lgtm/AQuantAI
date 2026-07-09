from fastapi import FastAPI

app = FastAPI(
    title="AQuantAI",
    version="0.1.0",
    description="A-share AI multi-factor quantitative research platform.",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "project": "AQuantAI",
        "status": "running",
        "version": "0.1.0",
        "phase": "Phase 0",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
