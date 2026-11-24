"""Keep the Power Query setup inventory in sync with the actual M templates."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_powerquery_readme_lists_each_template_exactly_once():
    query_dir = ROOT / "dashboard" / "powerquery"
    readme = (query_dir / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()
    start = lines.index("Load these queries:") + 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    listed = []
    for line in lines[start:]:
        if not line.startswith("- "):
            break
        listed.append(line[2:].strip())
    actual = sorted(path.stem for path in query_dir.glob("*.m"))

    assert len(listed) == len(set(listed)), "Power Query README contains duplicate query names"
    assert set(listed) == set(actual), {
        "missing_from_readme": sorted(set(actual) - set(listed)),
        "not_present_as_template": sorted(set(listed) - set(actual)),
    }
