from pathlib import Path

from app.outputs.facilities import load_facilities, suggest

CSV = """name,level,district,block,lat,lon,source,as_of
Synthetic PHC A,PHC,Testpur,B1,26.80,80.90,fixture,2026-01-01
Synthetic CHC B,CHC,Testpur,B1,26.90,80.95,fixture,2026-01-01
Synthetic SC C,SC_HWC,Testpur,B1,26.81,80.91,fixture,2026-01-01
Unsourced DH,DH,Testpur,B1,26.85,80.92,,
Other District PHC,PHC,Elsewhere,B9,26.80,80.90,fixture,2026-01-01
"""


def test_directory(tmp_path: Path) -> None:
    (tmp_path / "knowledge/facilities").mkdir(parents=True)
    (tmp_path / "knowledge/facilities/UP.csv").write_text(CSV)
    fs = load_facilities(tmp_path, "UP")
    assert "Unsourced DH" not in {f.name for f in fs}  # rows without a source are never shown
    assert [f.name for f in suggest(fs, "PHC", "Testpur")] == ["Synthetic PHC A", "Synthetic CHC B"]
    assert [f.name for f in suggest(fs, "CHC", "Testpur")] == ["Synthetic CHC B"]
    assert suggest(fs, "PHC", "Testpur", near=(26.91, 80.95))[0].name == "Synthetic CHC B"
    assert load_facilities(tmp_path, "BR") == [] and load_facilities(tmp_path, None) == []
