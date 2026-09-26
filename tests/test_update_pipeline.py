from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_market_data as umd


def test_alghaf_parser_prefers_largest_history_table(monkeypatch):
    html = """
    <html><body>
    <table>
      <tr><th>Date</th><th>Mid</th><th>Change</th><th>Unit</th></tr>
      <tr><td>24 September 2026</td><td>129.1</td><td>+2.4</td><td>USD/BBL</td></tr>
    </table>
    <table>
      <tr><th>Date</th><th>Mid</th><th>Change</th><th>Unit</th></tr>
      <tr><td>24 September 2026</td><td>129.1</td><td>+2.4</td><td>USD/BBL</td></tr>
      <tr><td>23 September 2026</td><td>126.7</td><td>-1.6</td><td>USD/BBL</td></tr>
      <tr><td>21 September 2026</td><td>128.8</td><td>-3.9</td><td>USD/BBL</td></tr>
    </table>
    </body></html>
    """
    monkeypatch.setattr(umd, "get", lambda url: html)
    out = umd.parse_alghaf("https://example.test/ron92", "ron92")
    assert len(out) == 3
    assert out.iloc[-1]["ron92"] == 129.1
    assert out.iloc[0]["date"].date().isoformat() == "2026-09-21"


def test_cache_bust_preserves_source_url():
    original = "https://example.com/path/history?mode=all"
    busted = umd._cache_bust(original)
    assert busted.startswith("https://example.com/path/history?")
    assert "mode=all" in busted
    assert "bfo_refresh=" in busted
