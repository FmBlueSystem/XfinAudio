"""Mach-O closure is contained, relocatable and native, without source writes."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("mac_dependencies", ROOT / "packaging/macos/dependencies.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_closure_resolves_loader_rpath_cycles_and_system_baseline(tmp_path):
    m = module()
    exe, lib, nested = [tmp_path / name for name in ["ffmpeg", "libcodec.dylib", "libmath.dylib"]]
    for p in [exe, lib, nested]:
        p.write_bytes(p.name.encode())
    entries = {
        exe: m.Info(("arm64",), (str(lib), "/usr/lib/libSystem.B.dylib"), (), None),
        lib: m.Info(("arm64",), ("@rpath/libmath.dylib",), ("@loader_path",), str(lib)),
        nested: m.Info(("arm64",), ("@loader_path/libcodec.dylib",), (), str(nested)),
    }
    assert set(m.dependency_closure(exe, read=lambda p: entries[p])) == {exe, lib, nested}


@pytest.mark.parametrize("kind", ["unresolved", "external", "wrong_arch", "bad_rpath", "bad_id"])
def test_final_audit_rejects_external_or_incompatible_runtime(tmp_path, kind):
    m = module()
    p = tmp_path / "ffmpeg"
    p.write_bytes(b"fixture")
    dependency = "@loader_path/missing.dylib" if kind == "unresolved" else "/opt/homebrew/Cellar/codec/lib.dylib"
    info = m.Info(
        ("x86_64",) if kind == "wrong_arch" else ("arm64",),
        () if kind in ["wrong_arch", "bad_rpath", "bad_id"] else (dependency,),
        ("/old/.venv/lib",) if kind == "bad_rpath" else (),
        "/opt/homebrew/Cellar/old.dylib" if kind == "bad_id" else None,
    )
    with pytest.raises(ValueError):
        m.audit_binary(p, tmp_path, p, read=lambda _: info)


def test_external_symlink_and_same_name_collision_fail_closed(tmp_path):
    m = module()
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.dylib"
    outside.write_bytes(b"outside")
    entry = root / "ffmpeg"
    entry.write_bytes(b"entry")
    (root / "link.dylib").symlink_to(outside)
    with pytest.raises(ValueError):
        m.audit_binary(entry, root, entry, read=lambda _: m.Info(("arm64",), ("@loader_path/link.dylib",), (), None))
    one, two = [tmp_path / name / "same.dylib" for name in ["a", "b"]]
    for p in [one, two]:
        p.parent.mkdir()
        p.write_bytes(p.parent.name.encode())
    with pytest.raises(ValueError):
        m.stage_closure(
            entry,
            tmp_path / "stage",
            closure={
                entry: m.Info(("arm64",), (), (), None),
                one: m.Info(("arm64",), (), (), None),
                two: m.Info(("arm64",), (), (), None),
            },
            run=lambda _: None,
        )


def test_final_audit_accepts_only_system_or_contained_relative_paths(tmp_path):
    m = module()
    entry, lib = tmp_path / "ffmpeg", tmp_path / "codec.dylib"
    entry.write_bytes(b"entry")
    lib.write_bytes(b"lib")
    info = m.Info(
        ("arm64",), ("@loader_path/codec.dylib", "/System/Library/Frameworks/CoreAudio.framework/CoreAudio"), (), None
    )
    m.audit_binary(entry, tmp_path, entry, read=lambda _: info)


def test_helper_executable_uses_its_own_loader_context(tmp_path):
    m = module()
    main = tmp_path / "Contents/MacOS/main"
    helper = tmp_path / "Contents/Frameworks/Helper.app/Contents/MacOS/helper"
    library = tmp_path / "Contents/Frameworks/codec.dylib"
    for p in [main, helper, library]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\xcf\xfa\xed\xfe")
    infos = {
        main: m.Info(("arm64",), (), (), None, True),
        helper: m.Info(("arm64",), ("@rpath/codec.dylib",), ("@executable_path/../../..",), None, True),
        library: m.Info(("arm64",), ("/usr/lib/libSystem.B.dylib",), (), "@rpath/codec.dylib"),
    }
    assert len(m.audit_tree(tmp_path, main, read=lambda p: infos[p])) == 3


def test_otool_parenthesized_helper_uses_open_descriptor(tmp_path, monkeypatch):
    import os

    m = module()
    binary = tmp_path / "Electron Helper (Renderer)"
    binary.write_bytes(b"\xcf\xfa\xed\xfe")

    def fake(args, **kwargs):
        if args[0].endswith("lipo"):
            return "arm64\n"
        assert args[-1].startswith("/dev/fd/")
        descriptor = int(args[-1].split("/")[-1])
        assert descriptor in kwargs["pass_fds"]
        assert os.read(descriptor, 4) == b"\xcf\xfa\xed\xfe"
        return {
            "-L": "descriptor:\n\t/usr/lib/libSystem.B.dylib (compatibility version 1)\n",
            "-D": "descriptor:\n",
            "-l": "",
            "-hv": "EXECUTE",
        }[args[1]]

    monkeypatch.setattr(m.subprocess, "check_output", fake)
    assert m.read_info(binary).executable is True
