import subprocess
import sys


def test_library_models_import_does_not_load_services_or_repositories() -> None:
    script = """
import sys
import xfinaudio.library.models  # noqa: F401
blocked = {
    "xfinaudio.library.scan_service",
    "xfinaudio.library.track_repository",
}
raise SystemExit(0 if blocked.isdisjoint(sys.modules) else 1)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False)

    assert result.returncode == 0


def test_audio_analysis_planning_import_does_not_load_analyzers() -> None:
    script = """
import sys
import xfinaudio.audio.analysis_planning  # noqa: F401
blocked = {
    "xfinaudio.audio.batch_analyzer",
    "xfinaudio.audio.spectral_profile",
}
raise SystemExit(0 if blocked.isdisjoint(sys.modules) else 1)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False)

    assert result.returncode == 0


def test_core_public_exports_resolve_on_demand() -> None:
    script = """
from xfinaudio.audio import AnalysisPlan, analyze_paths
from xfinaudio.library import TrackRecord, scan_folder
print(AnalysisPlan.__name__, analyze_paths.__name__, TrackRecord.__name__, scan_folder.__name__)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)

    assert result.returncode == 0
    assert result.stdout.strip() == "AnalysisPlan analyze_paths TrackRecord scan_folder"
