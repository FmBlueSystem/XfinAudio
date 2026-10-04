"""QA-only DMG packaging rejects unsafe inputs and records exact produced bytes."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEAL = "exact-source-seal"
APP_NAME = "XfinAudio Next.app"
IMAGE_NAME = "XfinAudio Next QA.dmg"


def module():
    spec = importlib.util.spec_from_file_location("mac_dmg", ROOT / "packaging/macos/dmg.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_app(tmp_path, *, seal=SEAL, bundle=APP_NAME, stage="post-final-signing"):
    app = tmp_path / "build" / APP_NAME
    licenses = app / "Contents/Resources/LICENSES"
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/MacOS/XfinAudio Next").write_text("sealed executable")
    licenses.mkdir(parents=True)
    for name in ("XfinAudio-NOTICE.md", "LICENSE", "LICENSES.chromium.html", "ffmpeg-input-provenance.json"):
        (licenses / name).write_text("notice " + name)
    (licenses / "FFmpeg-dependencies").mkdir()
    (licenses / "FFmpeg-dependencies/pkg.txt").write_text("dependency notice")
    manifest = {"source_sha256": seal, "bundle": bundle, "inventory_stage": stage}
    app.with_name(APP_NAME + ".native-manifest.json").write_text(json.dumps(manifest))
    return app


def runner(commands, *, snapshot=None, fail_verify=False, write=True):
    def run(command):
        commands.append(command)
        if command[1] == "verify":
            if fail_verify:
                raise subprocess.CalledProcessError(1, command)
            return
        staging = Path(command[command.index("-srcfolder") + 1])
        if snapshot is not None:
            snapshot["entries"] = sorted(p.name for p in staging.iterdir())
            snapshot["applications"] = (staging / "Applications").readlink()
        if write:
            Path(command[-1]).write_text("synthetic disk image")

    return run


def output(tmp_path):
    directory = tmp_path / "dist"
    directory.mkdir(exist_ok=True)
    return directory / IMAGE_NAME


def tree_digest(root):
    parts = []
    for path in sorted(root.rglob("*")):
        key = path.relative_to(root).as_posix()
        if path.is_symlink():
            parts.append(f"{key}:{path.readlink()}")
        elif path.is_dir():
            parts.append(f"{key}:dir")
        else:
            parts.append(f"{key}:{sha256(path)}")
    return "\n".join(parts)


def test_builds_fixed_qa_image_and_evidence_only_after_verification(tmp_path):
    d = module()
    app, out, commands, snapshot = synthetic_app(tmp_path), output(tmp_path), [], {}
    (app / "Contents/Resources/alias").symlink_to("LICENSES")
    sealed = tree_digest(app)
    d.package(app, SEAL, out, runner=runner(commands, snapshot=snapshot))
    assert [c[1] for c in commands] == ["create", "verify"]
    assert commands[0][commands[0].index("-volname") + 1] == "XfinAudio Next QA"
    assert snapshot["entries"] == ["Applications", APP_NAME]
    assert snapshot["applications"] == Path("/Applications")
    assert tree_digest(app) == sealed
    assert out.read_text() == "synthetic disk image"
    assert (out.parent / "XfinAudio Next QA.sha256").read_text() == f"{sha256(out)}  {IMAGE_NAME}\n"
    record = json.loads((out.parent / "XfinAudio Next QA.provenance.json").read_text())
    assert record["image_sha256"] == sha256(out)
    assert record["source_sha256"] == SEAL
    assert record["manifest_sha256"] == sha256(app.with_name(APP_NAME + ".native-manifest.json"))
    assert record["qa_only"] is True
    assert "not evaluated" in record["clearance"]
    assert record["byte_reproducibility"].startswith("not claimed")


@pytest.mark.parametrize("change", [{"seal": "stale"}, {"bundle": "Other.app"}, {"stage": "pre-final-signing"}])
def test_rejects_manifest_that_is_not_the_exact_post_signing_source(tmp_path, change):
    d = module()
    out = output(tmp_path)
    with pytest.raises(ValueError, match="manifest"):
        d.package(synthetic_app(tmp_path, **change), SEAL, out, runner=runner([]))
    assert not out.exists()


@pytest.mark.parametrize("name", ["release.dmg", "XfinAudio Next QA"])
def test_rejects_any_image_name_other_than_the_fixed_qa_basename(tmp_path, name):
    d = module()
    with pytest.raises(ValueError, match="fixed"):
        d.package(synthetic_app(tmp_path), SEAL, output(tmp_path).with_name(name), runner=runner([]))


def test_rejects_existing_output_and_output_inside_the_source_tree(tmp_path):
    d = module()
    app, existing = synthetic_app(tmp_path), output(tmp_path)
    existing.write_text("stale")
    with pytest.raises(ValueError, match="already exists"):
        d.package(app, SEAL, existing, runner=runner([]))
    existing.unlink()
    existing.with_name("XfinAudio Next QA.sha256").write_text("stale evidence")
    with pytest.raises(ValueError, match="already exists"):
        d.package(app, SEAL, existing, runner=runner([]))
    existing.with_name("XfinAudio Next QA.sha256").unlink()
    with pytest.raises(ValueError, match="outside the source tree"):
        d.package(app, SEAL, ROOT / IMAGE_NAME, runner=runner([]))
    assert not (ROOT / IMAGE_NAME).exists()


@pytest.mark.parametrize(
    "missing",
    [
        "Contents/MacOS/XfinAudio Next",
        "Contents/Resources/LICENSES/LICENSE",
        "Contents/Resources/LICENSES/ffmpeg-input-provenance.json",
        "Contents/Resources/LICENSES/FFmpeg-dependencies/pkg.txt",
    ],
)
def test_rejects_missing_executable_or_declared_notice(tmp_path, missing):
    d = module()
    app, out, commands = synthetic_app(tmp_path), output(tmp_path), []
    (app / missing).unlink()
    with pytest.raises(ValueError):
        d.package(app, SEAL, out, runner=runner(commands))
    assert commands == [] and not out.exists()


def test_rejects_symlinks_that_escape_the_staged_app(tmp_path):
    d = module()
    app, commands = synthetic_app(tmp_path), []
    outside = tmp_path / "outside"
    outside.mkdir()
    (app / "Contents/Resources/escape").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        d.package(app, SEAL, output(tmp_path), runner=runner(commands))
    assert commands == []
    staging = tmp_path / "stage"
    staging.mkdir()
    (staging / "sneaky").symlink_to(tmp_path / "build")
    with pytest.raises(ValueError, match="symlink"):
        d.stage(app, staging)


@pytest.mark.parametrize("mode", ["failed-verify", "missing-image"])
def test_failed_or_missing_image_leaves_no_accepted_artifact(tmp_path, mode):
    d = module()
    app, out = synthetic_app(tmp_path), output(tmp_path)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        d.package(
            app,
            SEAL,
            out,
            runner=runner([], fail_verify=mode == "failed-verify", write=mode != "missing-image"),
        )
    assert not out.exists()
    assert not (out.parent / "XfinAudio Next QA.sha256").exists()
    assert not (out.parent / "XfinAudio Next QA.provenance.json").exists()


def test_hashes_image_in_chunks_without_reading_it_whole(tmp_path, monkeypatch):
    d = module()
    app, out = synthetic_app(tmp_path), output(tmp_path)
    payload = b"0123456789abcdef" * 200_000

    def write_chunked_image(command):
        if command[1] == "verify":
            return
        Path(command[-1]).write_bytes(payload)

    def forbidden(self):
        raise AssertionError("sha256 must stream the image, not Path.read_bytes()")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    digest = d.package(app, SEAL, out, runner=write_chunked_image)
    expected = hashlib.sha256(payload).hexdigest()
    assert digest == expected
    assert (out.parent / "XfinAudio Next QA.sha256").read_text() == f"{expected}  {IMAGE_NAME}\n"
    record = json.loads((out.parent / "XfinAudio Next QA.provenance.json").read_text())
    assert record["image_sha256"] == expected


def test_failed_evidence_write_discards_image_and_both_sidecars(tmp_path, monkeypatch):
    d = module()
    app, out = synthetic_app(tmp_path), output(tmp_path)
    written = []
    real_write_text = Path.write_text

    def write_text(self, *args, **kwargs):
        written.append(self.name)
        if self.name == d.PROVENANCE_NAME:
            raise OSError("synthetic evidence failure")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_text)
    with pytest.raises(OSError, match="synthetic evidence failure"):
        d.package(app, SEAL, out, runner=runner([]))
    assert written[-1] == d.PROVENANCE_NAME
    assert not out.exists()
    assert not (out.parent / d.SHA_NAME).exists()
    assert not (out.parent / d.PROVENANCE_NAME).exists()
