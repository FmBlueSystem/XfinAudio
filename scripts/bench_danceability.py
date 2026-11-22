"""Per-stage benchmark for the danceability analyzer (S1: measure before changing).

Two pipelines are measured on the *same* tracks in the *same* process, interleaved
round by round, so a machine busy with another job does not bias one side:

``baseline``
    A frozen replica of the original ``analyze_danceability`` body (duration
    probe, ``librosa.load``, onset strength, pulse clarity, tempogram, STFT,
    HPSS, energy sums, score assembly), each stage timed separately.

``module``
    The same stage breakdown of the module as it exists right now. It asserts
    that its result equals ``analyze_danceability`` so it can never drift from
    the shipped code, and it is the side that changes when the module changes.

The script only reads audio files. The JSON it writes holds the per-stage
medians and the profile values needed to prove the values did not move.

Usage (from the repository root)::

    PYTHONPATH=src python scripts/bench_danceability.py --rounds 3
    PYTHONPATH=src python scripts/bench_danceability.py --gil

``--gil`` measures the thread scaling that decides the process-level parallelism
work: the same tracks on 1 thread and on N threads, reported as wall time, CPU
time and CPU-per-wall ratio. A ratio near N means the work releases the GIL.
"""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DEFAULT_AUDIO_ROOT = Path("/Volumes/dd/_Lossless/por_genero")
BASELINE_JSON = Path(tempfile.gettempdir()) / "xfinaudio-danceability-baseline.json"

# One track per genre so the sample is not a single kind of material.
GENRES = (
    "Classical",
    "Country",
    "Disco",
    "Funk",
    "Hip-Hop & R&B",
    "House & Electronic",
    "Jazz",
    "Pop & Dance",
    "Reggae & Dancehall",
    "Rock",
    "Soul",
    "Soundtrack & Theme",
    "Synth Pop & New Wave",
    "World & Latin",
)

# Kept identical to the module so the two pipelines describe the same excerpt.
SAMPLE_RATE = 22050
WINDOW_SECONDS = 45.0
N_FFT = 2048
HOP_LENGTH = 512
MIN_BEAT_LAG = 8
MAX_BEAT_LAG = 200
PERCUSSIVE_FLOOR = 0.30
PERCUSSIVE_CEILING = 0.52

STAGES = (
    "duration_probe",
    "load",
    "onset_strength",
    "pulse_clarity",
    "tempo_confidence",
    "stft",
    "hpss",
    "hpss_energy",
    "rest",
    "total",
)


@dataclass
class Timings:
    """Per-stage seconds collected over every track and round."""

    samples: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def add(self, stage: str, seconds: float) -> None:
        self.samples[stage].append(seconds)

    def medians(self) -> dict[str, float]:
        return {stage: statistics.median(self.samples[stage]) for stage in STAGES if self.samples[stage]}


def select_tracks(root: Path, limit: int) -> list[Path]:
    """Deterministic genre-spread sample: the first playable-length file per genre."""
    import soundfile

    tracks: list[Path] = []
    for genre in GENRES:
        folder = root / genre
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.flac")):
            try:
                seconds = float(soundfile.info(str(path)).duration)
            except Exception:
                continue
            if 60.0 <= seconds <= 900.0:
                tracks.append(path)
                break
        if len(tracks) >= limit:
            break
    return tracks


def _load_excerpt(path: Path, librosa, timings: Timings) -> tuple[np.ndarray, int]:
    started = time.perf_counter()
    try:
        track_duration = float(librosa.get_duration(path=path))
    except Exception:
        track_duration = None
    timings.add("duration_probe", time.perf_counter() - started)

    offset = 0.0
    if track_duration is not None and track_duration > WINDOW_SECONDS:
        offset = max(0.0, (track_duration / 2.0) - (WINDOW_SECONDS / 2.0))
    started = time.perf_counter()
    y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True, offset=offset, duration=WINDOW_SECONDS)
    if y.size == 0 and offset > 0.0:
        y, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True, duration=WINDOW_SECONDS)
    timings.add("load", time.perf_counter() - started)
    return y, int(sr)


def _score(pulse_clarity: float, tempo_confidence: float, percussive_ratio: float) -> dict[str, float]:
    gate = np.clip(
        (percussive_ratio - PERCUSSIVE_FLOOR) / (PERCUSSIVE_CEILING - PERCUSSIVE_FLOOR),
        0.0,
        1.0,
    )
    return {
        "score": float(np.clip(pulse_clarity * tempo_confidence * gate, 0.0, 1.0)),
        "pulse_clarity": pulse_clarity,
        "tempo_confidence": tempo_confidence,
        "percussive_ratio": percussive_ratio,
    }


def _pulse_clarity(onset_envelope: np.ndarray, librosa) -> float:
    centered = onset_envelope - onset_envelope.mean()
    autocorrelation = librosa.autocorrelate(centered, max_size=len(centered) // 2)
    zero_lag = float(autocorrelation[0])
    if zero_lag <= 0:
        return 0.0
    normalized = autocorrelation / zero_lag
    upper = min(len(normalized) - 1, MAX_BEAT_LAG)
    if upper <= MIN_BEAT_LAG:
        return 0.0
    return float(np.clip(np.max(normalized[MIN_BEAT_LAG:upper]), 0.0, 1.0))


def _tempo_confidence(onset_envelope: np.ndarray, sample_rate: float, librosa) -> float:
    tempogram = librosa.feature.tempogram(onset_envelope=onset_envelope, sr=sample_rate, hop_length=HOP_LENGTH).mean(
        axis=1
    )
    peak = float(tempogram.max())
    if peak <= 0:
        return 0.0
    profile = (tempogram / peak)[4:]
    if profile.size == 0:
        return 0.0
    dominant = float(profile.max())
    mean = float(profile.mean())
    if mean <= 0:
        return 0.0
    return float(np.clip(dominant * (dominant / mean) / 4.0, 0.0, 1.0))


def baseline_profile(path: Path, timings: Timings) -> dict[str, float] | None:
    """The original analyzer, stage by stage, frozen here as the A side."""
    import librosa

    started_total = time.perf_counter()
    y, sr = _load_excerpt(path, librosa, timings)
    if y.size == 0 or not np.any(y):
        return None

    started = time.perf_counter()
    onset_envelope = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    timings.add("onset_strength", time.perf_counter() - started)
    if onset_envelope.size < MAX_BEAT_LAG:
        return None

    started = time.perf_counter()
    pulse_clarity = _pulse_clarity(onset_envelope, librosa)
    timings.add("pulse_clarity", time.perf_counter() - started)
    started = time.perf_counter()
    tempo_confidence = _tempo_confidence(onset_envelope, sr, librosa)
    timings.add("tempo_confidence", time.perf_counter() - started)

    started = time.perf_counter()
    stft = librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH)
    timings.add("stft", time.perf_counter() - started)
    started = time.perf_counter()
    harmonic, percussive = librosa.decompose.hpss(stft)
    timings.add("hpss", time.perf_counter() - started)
    started = time.perf_counter()
    percussive_energy = float(np.abs(percussive).sum())
    harmonic_energy = float(np.abs(harmonic).sum())
    timings.add("hpss_energy", time.perf_counter() - started)
    started = time.perf_counter()
    total = percussive_energy + harmonic_energy
    percussive_ratio = 0.0 if total <= 0 else float(np.clip(percussive_energy / total, 0.0, 1.0))
    values = _score(pulse_clarity, tempo_confidence, percussive_ratio)
    timings.add("rest", time.perf_counter() - started)
    timings.add("total", time.perf_counter() - started_total)
    return values


def module_profile(path: Path, timings: Timings) -> dict[str, float] | None:
    """The module as shipped right now, timed stage by stage.

    Stage boundaries mirror ``xfinaudio.audio.danceability``; the guard at the
    end of every round guarantees this replica never drifts from it.
    """
    import librosa

    from xfinaudio.audio import danceability as module

    started_total = time.perf_counter()
    y, sr = _load_excerpt(path, librosa, timings)
    if y.size == 0 or not np.any(y):
        return None

    started = time.perf_counter()
    onset_envelope = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    timings.add("onset_strength", time.perf_counter() - started)
    if onset_envelope.size < module._MAX_BEAT_LAG:  # noqa: SLF001 - benchmark harness
        return None

    started = time.perf_counter()
    pulse_clarity = module._pulse_clarity(onset_envelope, librosa)  # noqa: SLF001
    timings.add("pulse_clarity", time.perf_counter() - started)
    started = time.perf_counter()
    tempo_confidence = module._tempo_confidence(onset_envelope, sr, librosa)  # noqa: SLF001
    timings.add("tempo_confidence", time.perf_counter() - started)

    started = time.perf_counter()
    magnitude = np.abs(librosa.stft(y, n_fft=module._N_FFT, hop_length=module._HOP_LENGTH))  # noqa: SLF001
    timings.add("stft", time.perf_counter() - started)
    started = time.perf_counter()
    harmonic, percussive = module._hpss_median_magnitudes(magnitude)  # noqa: SLF001
    timings.add("hpss", time.perf_counter() - started)
    started = time.perf_counter()
    percussive_mask = librosa.util.softmask(percussive, harmonic, power=2.0, split_zeros=True)
    harmonic_mask = librosa.util.softmask(harmonic, percussive, power=2.0, split_zeros=True)
    percussive_energy = float(np.sum(magnitude * percussive_mask))
    harmonic_energy = float(np.sum(magnitude * harmonic_mask))
    total_energy = percussive_energy + harmonic_energy
    percussive_ratio = 0.0 if total_energy <= 0 else float(np.clip(percussive_energy / total_energy, 0.0, 1.0))
    timings.add("hpss_energy", time.perf_counter() - started)

    started = time.perf_counter()
    values = _score(pulse_clarity, tempo_confidence, percussive_ratio)
    timings.add("rest", time.perf_counter() - started)
    timings.add("total", time.perf_counter() - started_total)

    shipped = module._percussive_ratio(y, librosa)  # noqa: SLF001
    if abs(shipped - percussive_ratio) > 1e-12:
        raise SystemExit(f"stage replica drifted from _percussive_ratio on {path}: {shipped} != {percussive_ratio}")
    return values


def _actual(path: Path) -> dict[str, float] | None:
    from xfinaudio.audio.danceability import analyze_danceability

    profile = analyze_danceability(path)
    if profile is None:
        return None
    return {
        "score": profile.score,
        "pulse_clarity": profile.pulse_clarity,
        "tempo_confidence": profile.tempo_confidence,
        "percussive_ratio": profile.percussive_ratio,
    }


def run_benchmark(tracks: list[Path], rounds: int) -> dict:
    before = Timings()
    after = Timings()
    values: dict[str, dict[str, dict[str, float]]] = {}
    for round_index in range(rounds):
        for track in tracks:
            # Alternate which pipeline goes first: the second decode of a file hits
            # a warm page cache, so a fixed order would always flatter one side.
            if round_index % 2 == 0:
                baseline = baseline_profile(track, before)
                module_values = module_profile(track, after)
            else:
                module_values = module_profile(track, after)
                baseline = baseline_profile(track, before)
            if round_index == 0:
                actual = _actual(track)
                if actual != module_values:
                    raise SystemExit(
                        "module stage replica drifted from analyze_danceability on "
                        f"{track}: {actual} != {module_values}"
                    )
                values[str(track)] = {
                    "baseline": baseline or {},
                    "module": module_values or {},
                    "actual": actual or {},
                }
    drift = 0.0
    drift_by_field: dict[str, float] = {}
    for track_values in values.values():
        for field_name, old in track_values["baseline"].items():
            new = track_values["module"].get(field_name)
            if new is None:
                raise SystemExit(f"module pipeline returned no {field_name}")
            difference = abs(new - old)
            drift = max(drift, difference)
            drift_by_field[field_name] = max(drift_by_field.get(field_name, 0.0), difference)
    before_medians = before.medians()
    after_medians = after.medians()
    return {
        "rounds": rounds,
        "tracks": [str(track) for track in tracks],
        "baseline_median_seconds": before_medians,
        "module_median_seconds": after_medians,
        "speedup": (before_medians["total"] / after_medians["total"] if after_medians.get("total") else None),
        "values": values,
        "max_abs_value_drift": drift,
        "max_abs_value_drift_by_field": drift_by_field,
    }


def run_gil(tracks: list[Path], workers: list[int], rounds: int) -> dict:
    """Thread scaling: wall, CPU and CPU-per-wall for each pipeline and worker count."""
    from xfinaudio.audio.danceability import analyze_danceability

    pipelines = {
        "baseline": lambda path: baseline_profile(path, Timings()),
        "module": analyze_danceability,
    }
    results: dict[str, dict[str, dict[str, float]]] = {}
    for name, run_one in pipelines.items():
        per_workers: dict[str, dict[str, float]] = {}
        for worker_count in workers:
            wall_samples: list[float] = []
            cpu_samples: list[float] = []
            for _ in range(rounds):
                started_wall = time.perf_counter()
                started_cpu = time.process_time()
                if worker_count == 1:
                    for track in tracks:
                        run_one(track)
                else:
                    with ThreadPoolExecutor(max_workers=worker_count) as pool:
                        list(pool.map(run_one, tracks))
                wall_samples.append(time.perf_counter() - started_wall)
                cpu_samples.append(time.process_time() - started_cpu)
            wall_median = statistics.median(wall_samples)
            cpu_median = statistics.median(cpu_samples)
            per_workers[str(worker_count)] = {
                "tracks": len(tracks),
                "wall_median_seconds": wall_median,
                "cpu_median_seconds": cpu_median,
                "cpu_per_wall": cpu_median / wall_median if wall_median else 0.0,
                "seconds_per_track": wall_median / len(tracks),
            }
        baseline_wall = per_workers[str(workers[0])]["wall_median_seconds"]
        for entry in per_workers.values():
            entry["speedup_vs_first"] = (
                baseline_wall / entry["wall_median_seconds"] if entry["wall_median_seconds"] else 0.0
            )
        results[name] = per_workers
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--tracks", type=int, default=12)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--gil", action="store_true", help="measure thread scaling instead of stages")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--json", type=Path, default=BASELINE_JSON)
    parser.add_argument("--label", default="current")
    arguments = parser.parse_args()

    tracks = select_tracks(arguments.root, arguments.tracks)
    if not arguments.gil and len(tracks) < 10:
        raise SystemExit(f"need at least 10 tracks, found {len(tracks)} under {arguments.root}")
    print(f"[{arguments.label}] {len(tracks)} tracks:")
    for track in tracks:
        print(f"  {track}")

    if arguments.gil:
        payload = {"label": arguments.label, "mode": "gil", "tracks": [str(t) for t in tracks]}
        payload["thread_scaling"] = run_gil(tracks, arguments.workers, arguments.rounds)
        print(json.dumps(payload["thread_scaling"], indent=2))
    else:
        payload = {"label": arguments.label, "mode": "stages", **run_benchmark(tracks, arguments.rounds)}
        print(
            json.dumps(
                {
                    key: payload[key]
                    for key in (
                        "baseline_median_seconds",
                        "module_median_seconds",
                        "speedup",
                        "max_abs_value_drift",
                        "max_abs_value_drift_by_field",
                    )
                },
                indent=2,
            )
        )
        print(json.dumps(payload["values"], indent=2))

    arguments.json.parent.mkdir(parents=True, exist_ok=True)
    arguments.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {arguments.json}")


if __name__ == "__main__":
    main()
