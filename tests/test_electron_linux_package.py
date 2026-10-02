"""Linux packaging fails closed and never silently depends on host Python or Qt."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "packaging/linux/build.py"


def module():
    spec = importlib.util.spec_from_file_location("linux_package", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def write(root: Path, name: str, text: str = "fixture") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_source_digest_detects_untracked_changes_but_ignores_generated_output(tmp_path):
    pack = module()
    write(tmp_path, "src/entry.py")
    initial = pack.source_digest(tmp_path)
    write(tmp_path, "desktop-electron/.out/main.js", "generated")
    assert pack.source_digest(tmp_path) == initial
    write(tmp_path, "packaging/linux/new.py", "new")
    assert pack.source_digest(tmp_path) != initial


def test_gate_requires_every_named_aggregate_gate_and_current_source(tmp_path):
    pack = module()
    report = {
        "project_root": str(tmp_path),
        "mode": "run",
        "overall_status": "passed",
        "source_sha256": pack.source_digest(tmp_path),
        "gates": [{"name": name, "status": "passed", "return_code": 0} for name in pack.REQUIRED_GATES],
    }
    pack.validate_gate(report, tmp_path)
    for field, value in [
        ("source_sha256", "stale"),
        ("overall_status", "failed"),
        ("gates", []),
        ("mode", "list"),
        ("project_root", "/other"),
    ]:
        with pytest.raises(ValueError):
            pack.validate_gate({**report, field: value}, tmp_path)
    bad = {**report, "gates": [*report["gates"][:-1], {**report["gates"][-1], "return_code": 1}]}
    with pytest.raises(ValueError):
        pack.validate_gate(bad, tmp_path)


@pytest.mark.parametrize("name", ["PySide6.QtCore", "PyQt5.QtWidgets", "shiboken6", "xfinaudio.desktop.app"])
def test_core_module_audit_rejects_qt_and_old_desktop(name):
    with pytest.raises(ValueError):
        module().assert_core_modules(["json", "xfinaudio.headless.backend", name])


def test_core_module_audit_accepts_headless_modules():
    module().assert_core_modules(["json", "numpy", "xfinaudio.headless.backend"])


@pytest.mark.parametrize("name", ["libQt6Core.so.6", "PySide6/QtCore.so", "node_modules/test.js"])
def test_tree_audit_rejects_qt_and_development_dependencies(tmp_path, name):
    write(tmp_path, name)
    with pytest.raises(ValueError):
        module().audit_tree(tmp_path)


def test_tree_audit_rejects_external_symlinks(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "escape").symlink_to(write(tmp_path, "private.txt"))
    with pytest.raises(ValueError):
        module().audit_tree(root)


def inputs(tmp_path):
    root, electron, core = [tmp_path / name for name in ("source", "electron", "core")]
    write(
        root,
        "desktop-electron/package.json",
        json.dumps({"version": "0.1.0", "devDependencies": {"electron": "44.5.1"}}),
    )
    write(root, "desktop-electron/.out/main/main.js")
    write(root, "desktop-electron/.out/renderer/index.html")
    write(root, "LICENSE")
    write(root, "NOTICE.md")
    write(electron, "electron").chmod(0o755)
    write(electron, "version", "44.5.1")
    write(electron, "LICENSE")
    write(electron, "LICENSES.chromium.html", "Chromium notices\r\n")
    write(electron, "resources/default_app.asar")
    write(core, "xfinaudio-core").chmod(0o755)
    write(core, "_internal/ffmpeg").chmod(0o755)
    write(core, "_internal/libpython3.12.so.1.0")
    return root, electron, core


def test_assembly_uses_existing_runtime_contract_without_python_launcher(tmp_path):
    root, electron, core = inputs(tmp_path)
    destination = tmp_path / "output"
    module().assemble(root, electron, core, destination)
    assert (destination / "xfinaudio").stat().st_mode & 0o111
    assert (destination / "resources/core/xfinaudio-core").is_file()
    assert (destination / "resources/core/_internal/ffmpeg").is_file()
    app = json.loads((destination / "resources/app/package.json").read_text())
    assert app["main"] == ".out/main/main.js"
    assert "devDependencies" not in app
    assert not (destination / "resources/default_app.asar").exists()
    assert (destination / "LICENSES/XfinAudio-LICENSE").exists()
    assert (destination / "LICENSE").exists()
    assert (destination / "LICENSES.chromium.html").read_bytes() == (electron / "LICENSES.chromium.html").read_bytes()
    with pytest.raises(ValueError):
        module().assemble(root, electron, core, destination)


@pytest.mark.parametrize(
    "owner,name",
    [("electron", "LICENSE"), ("electron", "LICENSES.chromium.html"), ("source", "LICENSE"), ("source", "NOTICE.md")],
)
@pytest.mark.parametrize("empty", [False, True])
def test_required_notices_refuse_assembly_before_output(tmp_path, owner, name, empty):
    root, electron, core = inputs(tmp_path)
    path = tmp_path / owner / name
    if empty:
        path.write_bytes(b"")
    else:
        path.unlink()
    with pytest.raises(ValueError, match="notice"):
        module().assemble(root, electron, core, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("missing", ["_internal/ffmpeg", "_internal/libpython3.12.so.1.0", "xfinaudio-core"])
def test_missing_runtime_dependency_refuses_assembly(tmp_path, missing):
    root, electron, core = inputs(tmp_path)
    (core / missing).unlink()
    with pytest.raises(ValueError):
        module().assemble(root, electron, core, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_output_inside_source_refused_and_electron_version_must_match(tmp_path):
    root, electron, core = inputs(tmp_path)
    with pytest.raises(ValueError):
        module().assemble(root, electron, core, root / "build")
    (electron / "version").write_text("wrong")
    with pytest.raises(ValueError):
        module().assemble(root, electron, core, tmp_path / "output")


def test_frozen_command_excludes_qt_and_bundles_python_and_ffmpeg(tmp_path, monkeypatch):
    write(
        tmp_path,
        "desktop-electron/requirements-headless.txt",
        "mutagen==1.48.1\npydantic==2.13.5\npydantic-core==2.46.5\nnumpy==2.5.3\nannotated-types==0.8.0\ntyping-extensions==4.16.0\ntyping-inspection==0.4.4\n",
    )
    pack = module()
    monkeypatch.setattr(pack, "python_notices", lambda: [])
    command = pack.freeze_command(tmp_path, tmp_path / "output", tmp_path / "ffmpeg")
    assert "--onedir" in command
    assert "--add-binary" in command
    assert str(tmp_path / "ffmpeg") + ":." in command
    for name in ("PySide6", "PyQt6", "PyQt5", "shiboken6", "xfinaudio.desktop"):
        index = command.index(name)
        assert command[index - 1] == "--exclude-module"
    assert "--noconsole" not in command


def test_ffmpeg_source_lock_is_pinned_to_official_audio_only_build():
    root = SCRIPT.parent
    lock = json.loads((root / "ffmpeg-source.json").read_text())
    assert lock["url"] == "https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz"
    assert len(lock["sha256"]) == 64
    flags = (root / "ffmpeg-configure.args").read_text().splitlines()
    assert "--disable-network" in flags
    assert "--disable-shared" in flags
    assert "--enable-static" in flags
    assert any("ebur128" in flag for flag in flags)
    assert any("mov" in flag for flag in flags)
    assert any("aac" in flag and "alac" in flag for flag in flags)
    assert not any("--enable-lib" in flag for flag in flags)


def test_frozen_command_retains_python_and_dependency_licenses(tmp_path, monkeypatch):
    write(
        tmp_path,
        "desktop-electron/requirements-headless.txt",
        "mutagen==1.48.1\npydantic==2.13.5\npydantic-core==2.46.5\nnumpy==2.5.3\nannotated-types==0.8.0\ntyping-extensions==4.16.0\ntyping-inspection==0.4.4\n",
    )
    pack = module()
    monkeypatch.setattr(pack, "python_notices", lambda: [])
    command = pack.freeze_command(tmp_path, tmp_path / "output", tmp_path / "ffmpeg")
    for name in (
        "mutagen",
        "pydantic",
        "pydantic-core",
        "numpy",
        "annotated-types",
        "typing-extensions",
        "typing-inspection",
    ):
        index = command.index(name, command.index("--add-binary") + 1)
        assert command[index - 1] == "--copy-metadata"
    assert any("LICENSE.txt:licenses/python" in item for item in command)


def test_ffmpeg_profile_supports_raw_pcm_verification():
    flags = (SCRIPT.parent / "ffmpeg-configure.args").read_text().splitlines()
    assert "--enable-muxer=null,pcm_s16le" in flags


def test_tree_audit_rejects_absolute_internal_symlink_for_relocation(tmp_path):
    target = write(tmp_path, "real.so")
    (tmp_path / "absolute.so").symlink_to(target)
    with pytest.raises(ValueError):
        module().audit_tree(tmp_path)
    (tmp_path / "absolute.so").unlink()
    (tmp_path / "relative.so").symlink_to("real.so")
    module().audit_tree(tmp_path)


def test_ffmpeg_validation_requires_version_true_peak_and_supported_formats(tmp_path):
    pack = module()
    executable = write(tmp_path, "ffmpeg")
    executable.chmod(0o755)
    output = {
        "-version": "ffmpeg version 7.1.1\nconfiguration: --disable-network",
        "-filters": "... ebur128 A->N EBU R128 scanner",
        "filter=ebur128": "peak true",
        "-decoders": "aac alac flac mp3 pcm_s16le",
        "-demuxers": "aiff flac mp3 mov wav",
        "-muxers": "null s16le",
        "-encoders": "pcm_s16le",
    }
    pack.validate_ffmpeg(executable, lambda args: output[args[-1]])
    for key in output:
        bad = {**output, key: "missing"}
        with pytest.raises(ValueError):
            pack.validate_ffmpeg(executable, lambda args, bad=bad: bad[args[-1]])


def test_ffmpeg_dependencies_allow_only_baseline_linux_libraries():
    pack = module()
    pack.validate_ffmpeg_dependencies(
        "linux-vdso.so.1\nlibc.so.6 => /lib/libc.so.6\nlibm.so.6 => /lib/libm.so.6\n/lib64/ld-linux-x86-64.so.2"
    )
    for dependency in ("libavcodec.so.61 => /lib/libavcodec.so.61", "libz.so.1 => not found"):
        with pytest.raises(ValueError):
            pack.validate_ffmpeg_dependencies(dependency)


def test_freeze_collects_profile_lazy_assets_and_all_locked_runtime_metadata(tmp_path, monkeypatch):
    write(
        tmp_path, "desktop-electron/requirements-headless.txt", "librosa==0.11.0\nsoundfile==0.14.0\nllvmlite==0.45.0\n"
    )
    pack = module()
    monkeypatch.setattr(pack, "python_notices", lambda: [])
    command = pack.freeze_command(tmp_path, tmp_path / "output", tmp_path / "ffmpeg")
    index = command.index("librosa")
    assert command[index - 1] == "--collect-all"
    assert any(command[i : i + 2] == ["--copy-metadata", "soundfile"] for i in range(len(command) - 1))
    assert any(command[i : i + 2] == ["--copy-metadata", "llvmlite"] for i in range(len(command) - 1))


def test_frozen_entry_confines_audio_decoder_path_without_affecting_development(tmp_path, monkeypatch):
    import os

    monkeypatch.delenv("NUMBA_CACHE_DIR", raising=False)
    monkeypatch.delenv("LIBROSA_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("NUMBA_CACHE_LOCATOR_CLASSES", raising=False)
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("core_entry", SCRIPT.parent / "core_entry.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    monkeypatch.setenv("PATH", "/external/tools")
    loaded.configure_runtime(None)
    assert os.environ["PATH"] == "/external/tools"
    loaded.configure_runtime(tmp_path, tmp_path / "data")
    assert os.environ["PATH"] == str(tmp_path)


def test_electron_gate_requires_real_integrations_without_skips():
    pack = module()
    pack.validate_electron_gate({"status": "passed", "passed": 100, "failed": 0, "skipped": 0})
    for report in (
        {},
        {"status": "failed", "passed": 1, "failed": 0, "skipped": 0},
        {"status": "passed", "passed": 100, "failed": 1, "skipped": 0},
        {"status": "passed", "passed": 100, "failed": 0, "skipped": 1},
        {"status": "passed", "passed": 0, "failed": 0, "skipped": 0},
    ):
        with pytest.raises(ValueError):
            pack.validate_electron_gate(report)


def test_freezer_environment_must_match_complete_hash_locked_dependency_set(tmp_path):
    lock = write(tmp_path, "requirements.txt", "pydantic-core==2.46.5 \\\n --hash=sha256:fixture\nlibrosa==0.11.0\n")
    pack = module()
    installed = {"pydantic_core": "2.46.5", "librosa": "0.11.0"}
    pack.validate_build_environment(lock, installed)
    for bad in ({}, {**installed, "librosa": "wrong"}, {**installed, "PySide6": "6.0"}):
        with pytest.raises(ValueError):
            pack.validate_build_environment(lock, bad)


def test_freeze_collects_current_scipy_vendored_dynamic_numpy_modules(tmp_path, monkeypatch):
    write(tmp_path, "desktop-electron/requirements-headless.txt", "scipy==1.18.1\n")
    pack = module()
    monkeypatch.setattr(pack, "python_notices", lambda: [])
    command = pack.freeze_command(tmp_path, tmp_path / "output", tmp_path / "ffmpeg")
    for name in ("scipy._external.array_api_compat.numpy.fft", "scipy._external.array_api_compat.numpy.linalg"):
        assert any(command[i : i + 2] == ["--hidden-import", name] for i in range(len(command) - 1))


def test_freezer_cache_stays_in_explicit_build_workspace(tmp_path):
    original = {"HOME": "/read-only", "PYINSTALLER_CONFIG_DIR": "/outside"}
    result = module().freeze_environment(original, tmp_path)
    assert result["PYINSTALLER_CONFIG_DIR"] == str(tmp_path / "pyinstaller-cache")
    assert result["HOME"] == "/read-only"
    assert original["PYINSTALLER_CONFIG_DIR"] == "/outside"


def bootstrap():
    spec = importlib.util.spec_from_file_location("runtime_bootstrap", SCRIPT.parent / "runtime_bootstrap.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize("hostile", [False, True])
def test_jit_cache_is_bound_to_trusted_data_dir_before_imports(tmp_path, monkeypatch, hostile):
    import os

    for name in ("NUMBA_CACHE_DIR", "LIBROSA_CACHE_DIR", "XDG_CACHE_HOME", "NUMBA_CACHE_LOCATOR_CLASSES"):
        if hostile:
            monkeypatch.setenv(name, str(tmp_path / "outside"))
        else:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PATH", "/host/python-and-ffmpeg")
    bundle, data = tmp_path / "readonly-bundle", tmp_path / "app-data"
    boot = bootstrap()
    boot.configure_runtime(bundle, boot.parse_data_dir(["--data-dir", str(data)]))
    assert os.environ["PATH"] == str(bundle)
    assert os.environ["NUMBA_CACHE_DIR"] == str(data / "cache/numba")
    assert "LIBROSA_CACHE_DIR" not in os.environ
    assert os.environ["XDG_CACHE_HOME"] == str(data / "cache")
    assert os.environ["NUMBA_CACHE_LOCATOR_CLASSES"] == "UserWideCacheLocator"
    assert (data / "cache/numba").is_dir()
    assert not (data / "cache/librosa").exists()
    assert not (tmp_path / "outside").exists()


def test_jit_bootstrap_refuses_symlink_cache_escape(tmp_path, monkeypatch):
    data, external = tmp_path / "app-data", tmp_path / "outside"
    data.mkdir()
    external.mkdir()
    (data / "cache").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError):
        bootstrap().configure_runtime(tmp_path / "bundle", data)
    assert list(external.iterdir()) == []


def test_jit_bootstrap_preserves_development_and_standard_help(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("NUMBA_CACHE_DIR", "/development-cache")
    boot = bootstrap()
    boot.configure_runtime(None, tmp_path / "data")
    assert os.environ["NUMBA_CACHE_DIR"] == "/development-cache"
    assert not (tmp_path / "data").exists()
    with pytest.raises(SystemExit) as help_exit:
        boot.parse_data_dir(["--help"])
    assert help_exit.value.code == 0
    assert boot.parse_data_dir(["--data-dir=/absolute/data"]) == Path("/absolute/data")


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--data-dir"],
        ["--data-dir", "relative"],
        ["--data-dir", "/tmp/../bad"],
        ["--data-dir", "/absolute", "--unknown"],
    ],
)
def test_jit_bootstrap_rejects_invalid_arguments_before_any_directory_creation(args, tmp_path, monkeypatch):
    created = []
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: created.append(args))
    with pytest.raises(SystemExit) as error:
        bootstrap().parse_data_dir(args)
    assert error.value.code == 2
    assert created == []


def test_smoke_uses_tagged_fixture_and_readonly_stream_properties(tmp_path):
    """The tagged smoke also preserves parser facts and bytes of untagged audio."""
    import wave

    from mutagen.id3 import TIT2
    from mutagen.wave import WAVE

    from xfinaudio.library.scan_service import read_mutagen_tags

    audio = tmp_path / "tone.wav"
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(44100)
        output.writeframes(b"\0\0" * 44100)
    untagged = audio.read_bytes()
    properties = read_mutagen_tags(audio)
    assert properties is not None and properties["__duration__"] == 1.0
    assert properties["__audio_properties__"] == {"audio_format": "WAV", "bitrate_kbps": 705.6}
    assert "TIT2" not in properties
    assert audio.read_bytes() == untagged
    tagged_audio = WAVE(audio)
    tagged_audio.add_tags()
    assert tagged_audio.tags is not None
    tagged_audio.tags.add(TIT2(encoding=3, text=["Synthetic tone"]))
    tagged_audio.save()
    tagged = audio.read_bytes()
    tags = read_mutagen_tags(audio)
    assert tags is not None and tags["TIT2"] == ["Synthetic tone"]
    assert audio.read_bytes() == tagged
    smoke = (SCRIPT.parent / "smoke.mjs").read_text()
    assert "before=await readFile(path.join(path.resolve(profileArg),'tone.wav'))" in smoke
    assert "toneWav()" not in smoke
