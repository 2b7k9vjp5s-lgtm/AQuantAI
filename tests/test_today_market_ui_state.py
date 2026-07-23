from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "today_market"
    / "static"
    / "today_market.js"
)


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_selection_change_invalidates_the_rendered_snapshot() -> None:
    script = _script()

    assert '[equitySelect, benchmarkSelect, sectorSelect].forEach' in script
    assert 'select.addEventListener("change", () => {' in script
    assert "snapshotRequestVersion += 1" in script
    assert 'snapshotButton.textContent = "查看本地市场快照"' in script
    assert "旧结果不会继续显示" in script
    assert "showPendingSnapshot(" in script


def test_async_catalog_and_snapshot_results_are_bound_to_exact_inputs() -> None:
    script = _script()

    assert "const requestVersion = ++catalogRequestVersion" in script
    assert "requestVersion !== catalogRequestVersion" in script
    assert "!sameBoundaries(boundary, boundaries())" in script
    assert "const requestBoundaries = { ...activeBoundaries }" in script
    assert "const requestSelection = currentSelection()" in script
    assert "requestVersion !== snapshotRequestVersion" in script
    assert "!sameBoundaries(requestBoundaries, activeBoundaries)" in script
    assert "!sameSelection(requestSelection, currentSelection())" in script


def test_technical_payload_remains_progressively_disclosed() -> None:
    script = _script()
    html = (
        Path(__file__).resolve().parents[1]
        / "today_market"
        / "static"
        / "today_market.html"
    ).read_text(encoding="utf-8")

    assert "technical.textContent = JSON.stringify(payload.technical_details" in script
    assert "<details>" in html
    assert "查看数据与技术详情" in html
