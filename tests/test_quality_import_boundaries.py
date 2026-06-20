import subprocess
import sys


def test_recommendation_quality_import_does_not_load_dj_readiness() -> None:
    script = """
import sys
import xfinaudio.quality.recommendation_quality  # noqa: F401
raise SystemExit(0 if "xfinaudio.quality.dj_readiness" not in sys.modules else 1)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False)

    assert result.returncode == 0


def test_quality_public_exports_resolve_on_demand() -> None:
    script = """
from xfinaudio.quality import RecommendationQualityReport, build_dj_readiness_report
print(RecommendationQualityReport.__name__, build_dj_readiness_report.__name__)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)

    assert result.returncode == 0
    assert result.stdout.strip() == "RecommendationQualityReport build_dj_readiness_report"
