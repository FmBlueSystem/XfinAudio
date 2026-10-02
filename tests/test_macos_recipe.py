"""Mac recipe accepts only sealed gates and contains application resources."""

import hashlib
import importlib.util
import json
import plistlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    sys.path.insert(0, str(ROOT / "packaging/macos"))
    spec = importlib.util.spec_from_file_location("mac_build", ROOT / "packaging/macos/build.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_mac_freeze_has_own_entry_locator_native_architecture_and_no_qt(tmp_path, monkeypatch):
    m = module()
    tools = m.shared_tools(ROOT)
    monkeypatch.setattr(tools, "python_notices", lambda: [])
    monkeypatch.setattr(m, "shared_tools", lambda root: tools)
    command = m.freeze_command(ROOT, tmp_path, tmp_path / "ffmpeg")
    assert str(ROOT / "packaging/macos/core_entry.py") in command
    assert str(ROOT / "packaging/linux/core_entry.py") not in command
    assert "mac_numba_cache" in command
    assert command[command.index("--target-architecture") + 1] == "arm64"
    assert "PySide6" in command and "xfinaudio.desktop" in command


def test_cross_host_gate_keeps_origin_and_requires_exact_source(tmp_path):
    m = module()
    tools = m.shared_tools(ROOT)
    report = {
        "project_root": "/cloud/owner/source",
        "source_sha256": tools.source_digest(ROOT),
        "mode": "run",
        "overall_status": "passed",
        "gates": [{"name": n, "status": "passed", "return_code": 0} for n in tools.REQUIRED_GATES],
        "electron_tests": {"status": "passed", "passed": 360, "failed": 0, "skipped": 0},
    }
    assert m.validate_gate(report, ROOT) == "/cloud/owner/source"
    for key, value in [
        ("source_sha256", "stale"),
        ("mode", "list"),
        ("gates", []),
        ("electron_tests", {"status": "passed", "passed": 360, "failed": 0, "skipped": 1}),
    ]:
        with pytest.raises(ValueError):
            m.validate_gate({**report, key: value}, ROOT)
    assert report["project_root"] == "/cloud/owner/source"


def assembly_inputs(tmp_path):
    root, electron, core = [tmp_path / name for name in ["source", "electron", "core"]]
    for folder in [
        root / "desktop-electron/.out/main",
        root / "desktop-electron/.out/renderer",
        electron / "Electron.app/Contents/MacOS",
        electron / "Electron.app/Contents/Resources",
        core / "_internal",
    ]:
        folder.mkdir(parents=True)
    (root / "desktop-electron/.out/main/main.js").write_text("compiled main")
    (root / "desktop-electron/.out/renderer/index.html").write_text("local renderer")
    (root / "desktop-electron/package.json").write_text(
        json.dumps({"version": "0.1.0", "devDependencies": {"electron": "44.5.1"}})
    )
    (root / "LICENSE").write_text("GPL3")
    (root / "NOTICE.md").write_bytes(b"Project notices\r\n")
    (electron / "LICENSE").write_bytes(b"Electron license\r\n")
    (electron / "LICENSES.chromium.html").write_bytes(b"Chromium notices\r\n")
    (electron / "version").write_text("44.5.1")
    (electron / "Electron.app/Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Electron"}))
    (electron / "Electron.app/Contents/MacOS/Electron").write_bytes(b"fixture")
    (electron / "Electron.app/Contents/Resources/default_app.asar").write_bytes(b"default")
    (core / "xfinaudio-core").write_bytes(b"core")
    (core / "_internal/ffmpeg").write_bytes(b"decoder")
    return root, electron, core


def test_assembly_uses_electron_resources_and_never_overwrites(tmp_path):
    m = module()
    root, electron, core = assembly_inputs(tmp_path)
    app = tmp_path / "XfinAudio Next.app"
    m.assemble(root, electron, core, app)
    resources = app / "Contents/Resources"
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "XfinAudio Next"
    assert (app / "Contents/MacOS" / info["CFBundleExecutable"]).read_bytes() == b"fixture"
    assert not (app / "Contents/MacOS/Electron").exists()
    assert info["CFBundleExecutable"].casefold() != "electron"
    assert (resources / "app/.out/main/main.js").is_file()
    assert (resources / "core/xfinaudio-core").is_file()
    assert not (resources / "default_app.asar").exists()
    assert (resources / "LICENSES/XfinAudio-NOTICE.md").read_bytes() == (root / "NOTICE.md").read_bytes()
    for name in ("LICENSE", "LICENSES.chromium.html"):
        assert (resources / "LICENSES" / name).read_bytes() == (electron / name).read_bytes()
    assert (
        plistlib.loads((app / "Contents/Info.plist").read_bytes())["CFBundleIdentifier"]
        == "io.bluesystem.xfinaudio.next"
    )
    with pytest.raises(ValueError):
        m.assemble(root, electron, core, app)


@pytest.mark.parametrize(
    "owner,name",
    [("electron", "LICENSE"), ("electron", "LICENSES.chromium.html"), ("source", "LICENSE"), ("source", "NOTICE.md")],
)
@pytest.mark.parametrize("empty", [False, True])
def test_required_notices_refuse_assembly_before_output(tmp_path, owner, name, empty):
    root, electron, core = assembly_inputs(tmp_path)
    path = tmp_path / owner / name
    if empty:
        path.write_bytes(b"")
    else:
        path.unlink()
    with pytest.raises(ValueError, match="notice"):
        module().assemble(root, electron, core, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_final_manifest_hashes_signed_bytes_outside_app(tmp_path, monkeypatch):
    m = module()
    app = tmp_path / "XfinAudio Next.app"
    core = app / "Contents/Resources/core"
    electron = app / "Contents/MacOS/XfinAudio Next"
    core.mkdir(parents=True)
    electron.parent.mkdir(parents=True)
    (core / "xfinaudio-core").write_bytes(b"core before signing")
    electron.write_bytes(b"electron before signing")
    events = []

    def run(command, **kwargs):
        assert kwargs == {"check": True}
        assert command[0] == "/usr/bin/codesign" and command[-1] == str(app)
        if "--sign" in command:
            assert command[command.index("--sign") + 1] == "-"
            events.append("sign")
            electron.write_bytes(b"electron after signing")
            (core / "xfinaudio-core").write_bytes(b"core after signing")
        else:
            assert "--verify" in command and "--strict" in command
            events.append("verify")

    def audit(root, executable, **kwargs):
        assert events[:2] == ["sign", "verify"]
        events.append("core audit" if root == core else "electron audit")
        assert kwargs == ({} if root == core else {"exclude": core})
        return [
            {
                "path": executable.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            }
        ]

    monkeypatch.setattr(m.subprocess, "run", run)
    monkeypatch.setattr(m, "audit_tree", audit)
    m.sign_and_record_final_manifest(app, "exact-source-seal")
    manifest_path = app.with_name(app.name + ".native-manifest.json")
    assert manifest_path.parent == app.parent
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_sha256"] == "exact-source-seal"
    assert manifest["inventory_stage"] == "post-final-signing"
    assert manifest["electron_native_inventory"][0]["sha256"] == hashlib.sha256(electron.read_bytes()).hexdigest()
    assert (
        manifest["core_native_inventory"][0]["sha256"]
        == hashlib.sha256((core / "xfinaudio-core").read_bytes()).hexdigest()
    )
    assert events == ["sign", "verify", "core audit", "electron audit"]
    assert not list(app.rglob("*manifest.json"))
