import subprocess
import sys


def test_saved_playlists_import_does_not_load_sibling_workflows() -> None:
    script = """
import sys
import xfinaudio.application.saved_playlists  # noqa: F401
blocked = {
    "xfinaudio.application.playlist_workflow",
    "xfinaudio.application.vertical_playlist_flow",
}
raise SystemExit(0 if blocked.isdisjoint(sys.modules) else 1)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False)

    assert result.returncode == 0


def test_application_public_exports_resolve_on_demand() -> None:
    script = """
from xfinaudio.application import PlaylistWorkflowService, SavedPlaylistService, VerticalPlaylistFlow
print(PlaylistWorkflowService.__name__, SavedPlaylistService.__name__, VerticalPlaylistFlow.__name__)
"""

    result = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)

    assert result.returncode == 0
    assert result.stdout.strip() == "PlaylistWorkflowService SavedPlaylistService VerticalPlaylistFlow"
