from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "industry_analysis" / "static"


def test_owner_context_confirmation_is_explicit_fail_closed_and_local() -> None:
    html = (ROOT / "owner_acceptance.html").read_text(encoding="utf-8")
    script = (ROOT / "owner_context_confirmation.js").read_text(encoding="utf-8")

    assert "owner_context_confirmation.js" in html
    assert html.index("owner_acceptance.js") < html.index(
        "owner_context_confirmation.js"
    )
    assert 'checkbox.id = "owner-context-confirm"' in script
    assert "Research Case、Industry Map 和地图修订" in script
    assert "不能在提交时更换或按名称猜测" in script
    assert 'form.addEventListener(' in script
    assert '"submit"' in script
    assert "event.preventDefault()" in script
    assert "event.stopImmediatePropagation()" in script
    assert "checkbox.disabled || !checkbox.checked" in script
    assert "MutationObserver" in script
    assert "JSON.parse(technical.textContent" in script

    forbidden = (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "http://",
        "https://",
    )
    assert all(token not in script for token in forbidden)
