"""Keep the Power Query setup inventory in sync with the actual M templates."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_powerquery_readme_lists_each_template_exactly_once():
    query_dir = ROOT / "dashboard" / "powerquery"
    readme = (query_dir / "README.md").read_text(encoding="utf-8")
    section = readme.split("Load these queries:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    listed = re.findall(r"^- ([A-Za-z0-9_]+)$", section, flags=re.MULTILINE)
    actual = sorted(path.stem for path in query_dir.glob("*.m"))

    assert len(listed) == len(set(listed)), "Power Query README contains duplicate query names"
    assert set(listed) == set(actual), {
        "missing_from_readme": sorted(set(actual) - set(listed)),
        "not_present_as_template": sorted(set(listed) - set(actual)),
    }
