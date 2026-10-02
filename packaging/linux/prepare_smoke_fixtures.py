"""Copy synthetic fixtures and add minimal metadata, proving decoded PCM unchanged."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from shutil import copy2

from mutagen import File
from mutagen.id3 import ID3, TIT2
from mutagen.mp4 import MP4

source, target, ffmpeg = map(Path, sys.argv[1:])
if target.exists():
    raise ValueError("Choose a new fixture output directory")
target.mkdir(parents=True)
report = []
for name in ("tone.wav", "tone.flac", "tone.mp3", "tone.aac.m4a", "tone.alac.m4a", "tone.aiff"):
    original, output = source / name, target / name
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    copy2(original, output)
    audio = File(output)
    if audio.tags is None:
        audio.add_tags()
    if isinstance(audio.tags, ID3):
        audio.tags.add(TIT2(encoding=3, text=["Synthetic tone"]))
    elif isinstance(audio, MP4):
        audio["\xa9nam"] = ["Synthetic tone"]
    else:
        audio["TITLE"] = ["Synthetic tone"]
    audio.save()

    def pcm(path):
        decoded = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-"],
            capture_output=True,
            check=True,
        ).stdout
        return hashlib.sha256(decoded).hexdigest()

    assert pcm(original) == pcm(output)
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
    assert File(output).tags is not None
    report.append(
        {
            "name": name,
            "original_unchanged_sha256": original_hash,
            "tagged_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "pcm_identical": True,
        }
    )
(target / "fixture-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
print(target)
