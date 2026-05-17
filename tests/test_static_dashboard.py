from pathlib import Path


def test_dashboard_static_files_exist_and_reference_safe_api_endpoints():
    root = Path(__file__).resolve().parents[1]
    index = root / "electricitybill" / "static" / "index.html"
    styles = root / "electricitybill" / "static" / "styles.css"
    script = root / "electricitybill" / "static" / "app.js"

    assert index.exists()
    assert styles.exists()
    assert script.exists()

    index_text = index.read_text(encoding="utf-8")
    script_text = script.read_text(encoding="utf-8")

    assert "寝室电费监控" in index_text
    assert "refreshButton" in index_text
    assert "currentBalance" in index_text
    assert "balanceChart" in index_text
    assert "deltaChart" in index_text
    assert "https://cdn.jsdelivr.net/npm/chart.js" in index_text
    assert 'fetch("/api/status")' in script_text
    assert 'fetch("/api/readings")' in script_text
    assert 'fetch("/api/refresh", { method: "POST" })' in script_text
    assert "try" in script_text
    assert "catch" in script_text
    assert "response.ok" in script_text
    assert "刷新失败" in script_text
    assert "refreshButton.disabled" in script_text
    combined = index_text + script_text
    assert "synjones-auth" not in combined
    assert "SYNJONES_AUTH" not in combined
    assert "bearer" not in combined.lower()
