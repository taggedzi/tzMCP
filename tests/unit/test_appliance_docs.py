from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_supported_appliance_docs_keep_host_browser_out_of_scope():
    text = (ROOT / "docs" / "appliance.md").read_text(encoding="utf-8").lower()
    assert "host browser" in text
    assert "windows proxy" in text
    assert "host trust store" in text
    assert "no production ova" in text
