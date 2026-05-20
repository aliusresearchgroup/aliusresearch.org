from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUDIO_DIR = Path(
    r"C:\Users\cogpsy-vrlab\Downloads\40 Logo Intro Music-20260520T093651Z-3-001\40 Logo Intro Music"
)
DEFAULT_TEMPLATE = ROOT / "docs" / "assets" / "brand" / "alius-logo.svg"
DEFAULT_OUTPUT = ROOT / "output" / "logo-music-sync" / "20260520"

FPS = 30
FRAME_SYNC_LEAD = 0.5 / FPS
SAMPLE_RATE = 44100
VIEWPORT = {"width": 1428, "height": 692}
EVENTS = ["middle_leaf", "left_leaf", "right_leaf", "A", "L", "I", "U", "S", "settle"]
LETTER_BASES = {
    "A": 3.86,
    "L": 4.22,
    "I": 4.49,
    "U": 4.66,
    "S": 5.02,
}
LETTER_GROUPS = {
    "A": "alius-letter-a-liquid",
    "L": "alius-letter-l-liquid",
    "I": "alius-letter-i-liquid",
    "U": "alius-letter-u-liquid",
    "S": "alius-letter-s-liquid",
}
LEAF_PATHS = {
    "middle_leaf": ("middle-leaf-growth", "middle-leaf", 2.0 / 2.75, 6.55),
    "left_leaf": ("left-leaf-growth", "left-leaf", 1.25 / 2.75, 6.15),
    "right_leaf": ("right-leaf-growth", "right-leaf", 1.0, 6.95),
}


@dataclass
class Track:
    number: int
    name: str
    slug: str
    path: Path
    duration: float


@dataclass
class CueProfile:
    track: Track
    peaks: list[dict[str, float]]
    leaf_cues: list[dict[str, float]]
    word_cues: list[dict[str, float]]
    leaf_score: float
    word_score: float


@dataclass
class CompositePair:
    index: int
    leaf: CueProfile
    word: CueProfile
    score: float
    transition_score: float


def run(cmd: list[str], *, input_bytes: bytes | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=input_bytes,
        cwd=str(cwd) if cwd else None,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return found


def ffprobe_duration(ffprobe: str, path: Path) -> float:
    proc = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ]
    )
    return float(proc.stdout.decode("utf-8").strip())


def decode_audio(ffmpeg: str, path: Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    proc = run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            str(sr),
            "-",
        ]
    )
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    if audio.size == 0:
        raise RuntimeError(f"No decoded samples for {path}")
    return np.nan_to_num(audio, copy=False)


def write_wav(path: Path, audio: np.ndarray, sr: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        audio = audio * (0.98 / peak)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sr)
        out.writeframes(pcm16.tobytes())


def slugify(name: str, number: int) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^\s*\d+\s*", "", stem).strip().lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return f"{number:02d}-{stem or 'intro'}"


def list_tracks(audio_dir: Path, ffprobe: str) -> list[Track]:
    files = [p for p in audio_dir.iterdir() if p.is_file() and p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}]

    def track_number(path: Path) -> int:
        match = re.match(r"\s*(\d+)", path.name)
        return int(match.group(1)) if match else 9999

    tracks = []
    for path in sorted(files, key=lambda p: (track_number(p), p.name.lower())):
        number = track_number(path)
        tracks.append(Track(number, path.name, slugify(path.name, number), path, ffprobe_duration(ffprobe, path)))
    return tracks


def frame_rms(audio: np.ndarray, sr: int = SAMPLE_RATE) -> tuple[np.ndarray, np.ndarray]:
    win = max(1, int(0.050 * sr))
    hop = max(1, int(0.025 * sr))
    if audio.size < win:
        audio = np.pad(audio, (0, win - audio.size))
    count = 1 + (audio.size - win) // hop
    shape = (count, win)
    strides = (audio.strides[0] * hop, audio.strides[0])
    frames = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    times = (np.arange(count) * hop + win * 0.5) / sr
    return times, rms


def smooth(values: np.ndarray, radius: int) -> np.ndarray:
    if values.size == 0 or radius <= 0:
        return values
    kernel = np.ones(radius * 2 + 1, dtype=np.float32)
    kernel /= kernel.sum()
    return np.convolve(values, kernel, mode="same")


def detect_peaks(audio: np.ndarray, duration: float) -> list[dict[str, float]]:
    times, rms = frame_rms(audio)
    env = smooth(np.log1p(rms * 18.0), 3)
    if env.size < 3:
        return [{"time": 0.05, "score": 1.0}]
    flux = np.maximum(np.diff(env, prepend=env[0]), 0.0)
    energy_norm = env / (float(env.max()) + 1e-7)
    flux_norm = flux / (float(flux.max()) + 1e-7)
    score = smooth(flux_norm * 0.78 + energy_norm * 0.22, 2)
    threshold = max(float(np.percentile(score, 70)), float(score.max()) * 0.18)
    candidates: list[tuple[float, float]] = []
    for i in range(1, score.size - 1):
        if score[i] >= score[i - 1] and score[i] >= score[i + 1] and score[i] >= threshold:
            candidates.append((float(times[i]), float(score[i])))
    if energy_norm[0] > 0.20:
        candidates.append((0.04, float(energy_norm[0] + 0.15)))
    candidates.sort(key=lambda item: item[1], reverse=True)
    selected: list[tuple[float, float]] = []
    min_sep = 0.18
    for time, value in candidates:
        if 0.02 <= time <= duration - 0.05 and all(abs(time - existing) >= min_sep for existing, _ in selected):
            selected.append((time, value))
        if len(selected) >= 32:
            break
    selected.sort()
    return [{"time": round(t, 4), "score": round(s, 4)} for t, s in selected]


def target_fractions(duration: float) -> list[float]:
    if duration < 5.25:
        return [0.02, 0.08, 0.15, 0.28, 0.39, 0.50, 0.61, 0.73, 0.88]
    if duration < 7.0:
        return [0.03, 0.10, 0.18, 0.31, 0.42, 0.52, 0.62, 0.74, 0.88]
    return [0.04, 0.12, 0.21, 0.34, 0.44, 0.53, 0.62, 0.73, 0.88]


def choose_event_times(peaks: list[dict[str, float]], duration: float) -> dict[str, float]:
    fractions = target_fractions(duration)
    min_gap = 0.115 if duration < 5.25 else (0.145 if duration < 7.0 else 0.19)
    # Existing website leaf morphs are invisible at the very start of their
    # opacity curves. Keep a small blank lead, then map the first usable hits
    # to the first visible moments of those existing curves.
    blank_lead = min(0.42, max(0.24, duration * 0.045))
    window = max(0.18, min(0.75, duration * 0.11))
    chosen: dict[str, float] = {}
    used: set[int] = set()

    def next_chronological_peak(after: float, before: float) -> tuple[float | None, int | None]:
        for peak_i, peak in enumerate(peaks):
            if peak_i in used:
                continue
            t = float(peak["time"])
            if after <= t <= before:
                return t, peak_i
        return None, None

    # The first audible/logo events should be the three leaf sprout starts.
    # Pick them chronologically, so the visual intro follows the music's first hits
    # instead of distributing leaf starts along an abstract timeline.
    prev = blank_lead - min_gap
    leaf_latest = max(blank_lead, duration * (0.43 if duration < 5.25 else 0.38))
    for name in ["middle_leaf", "left_leaf", "right_leaf"]:
        low = prev + min_gap
        high = max(low, leaf_latest)
        value, peak_i = next_chronological_peak(low, high)
        if value is None:
            value = low
        else:
            used.add(peak_i)
        chosen[name] = round(min(value, duration - 0.72), 3)
        prev = chosen[name]

    # Letters are subsequent events. They still prefer detected musical features,
    # but they cannot preempt the three leaf sprout starts.
    prev = chosen["right_leaf"]
    letter_events = ["A", "L", "I", "U", "S", "settle"]
    for idx, (name, fraction) in enumerate(zip(letter_events, fractions[3:])):
        remaining = len(letter_events) - idx - 1
        target = duration * fraction
        low = prev + min_gap
        high = max(low, duration - 0.12 - remaining * min_gap)
        target = min(max(target, low), high)
        best_i = None
        best_score = -1.0
        for peak_i, peak in enumerate(peaks):
            if peak_i in used:
                continue
            t = peak["time"]
            if t < low or t > high or abs(t - target) > window:
                continue
            score = peak["score"] / (1.0 + abs(t - target) * 1.8)
            if score > best_score:
                best_score = score
                best_i = peak_i
        if best_i is not None:
            value = float(peaks[best_i]["time"])
            used.add(best_i)
        else:
            value = target
        value = min(max(value, low), high)
        chosen[name] = round(value, 3)
        prev = value
    chosen["settle"] = min(duration - 0.08, max(chosen["settle"], chosen["S"] + min_gap))
    return chosen


def tagline_window(events: dict[str, float], duration: float) -> dict[str, float]:
    start = min(max(events["right_leaf"] + 0.35, events["A"] - 0.2), duration - 0.8)
    end = max(events["settle"], duration - 0.22)
    return {"tagline_start": round(start, 3), "tagline_end": round(end, 3)}


def fmt_s(seconds: float) -> str:
    value = f"{seconds:.3f}".rstrip("0").rstrip(".")
    if value in {"", "-0"}:
        value = "0"
    return value + "s"


def parse_seconds(value: str) -> float | None:
    if not value or not value.endswith("s"):
        return None
    try:
        return float(value[:-1])
    except ValueError:
        return None


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def retime_svg(template: Path, out_path: Path, events: dict[str, float], duration: float) -> None:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(template)
    root = tree.getroot()

    def local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    def by_id(element_id: str):
        for elem in root.iter():
            if elem.attrib.get("id") == element_id:
                return elem
        return None

    def first_positive_key_fraction(anim) -> float:
        if anim is None:
            return 0.0
        values = [v.strip() for v in anim.attrib.get("values", "").split(";")]
        key_times = [parse_float(v.strip()) for v in anim.attrib.get("keyTimes", "").split(";")]
        if not values or not key_times or len(values) != len(key_times):
            return 0.0
        first_positive = None
        for i, value in enumerate(values):
            parsed = parse_float(value)
            if parsed is not None and parsed > 0:
                first_positive = i
                break
        if first_positive is None:
            return 0.0
        visible_key = key_times[max(0, first_positive - 1)]
        return max(0.0, min(1.0, visible_key or 0.0))

    def first_visible_offset(anim) -> float:
        old_dur = parse_seconds(anim.attrib.get("dur", "")) or 0.0
        return first_positive_key_fraction(anim) * old_dur

    first_letter = events["A"]
    for event_name, (growth_id, final_id, sway_ratio, sway_dur) in LEAF_PATHS.items():
        growth_path = by_id(growth_id)
        final_path = by_id(final_id)
        if growth_path is None or final_path is None:
            raise RuntimeError(f"Missing leaf path: {growth_id} or {final_id}")
        growth_opacity = next(
            (
                child
                for child in growth_path
                if local_name(child.tag) == "animate" and child.attrib.get("attributeName") == "opacity"
            ),
            None,
        )
        target_visible = events[event_name]
        growth_dur = min(2.75, max(0.55, first_letter - target_visible + 0.12))
        old_growth_dur = parse_seconds(growth_opacity.attrib.get("dur", "")) if growth_opacity is not None else None
        visible_offset = first_visible_offset(growth_opacity) if growth_opacity is not None else 0.0
        # Begin may be negative, but the preserved opacity keyTimes keep the
        # first frame blank until the selected music hit reaches the original
        # website curve's first visible point.
        scaled_visible_offset = visible_offset * (growth_dur / (old_growth_dur or growth_dur))
        start = target_visible - FRAME_SYNC_LEAD - scaled_visible_offset
        growth_path.set("opacity", "0")
        final_path.set("opacity", "0")
        for anim in [child for child in growth_path if local_name(child.tag) == "animate"]:
            if anim.attrib.get("attributeName") in {"d", "opacity"}:
                anim.set("begin", fmt_s(start))
                anim.set("dur", fmt_s(growth_dur))
        for anim in [child for child in final_path if local_name(child.tag) == "animate"]:
            attr = anim.attrib.get("attributeName")
            if attr == "opacity":
                anim.set("begin", fmt_s(start))
                anim.set("dur", fmt_s(growth_dur))
            elif attr == "d" and anim.attrib.get("repeatCount") == "indefinite":
                anim.set("begin", fmt_s(start + growth_dur * sway_ratio))
                anim.set("dur", fmt_s(sway_dur))

    letter_order = ["A", "L", "I", "U", "S"]
    for idx, letter in enumerate(letter_order):
        group = by_id(LETTER_GROUPS[letter])
        if group is None:
            raise RuntimeError(f"Missing letter group: {LETTER_GROUPS[letter]}")
        base = LETTER_BASES[letter]
        next_time = events[letter_order[idx + 1]] if idx + 1 < len(letter_order) else events["settle"]
        available = max(0.18, next_time - events[letter])
        baseline_span = 0.60 if letter != "S" else 0.48
        scale = min(1.22, max(0.58, available * 0.88 / baseline_span))
        for anim in [child for child in group.iter() if local_name(child.tag) == "animate"]:
            old_begin = parse_seconds(anim.attrib.get("begin", ""))
            if old_begin is not None:
                anim.set("begin", fmt_s(events[letter] - FRAME_SYNC_LEAD + (old_begin - base) * scale))
            old_dur = parse_seconds(anim.attrib.get("dur", ""))
            if old_dur is not None and old_dur > 0.001:
                anim.set("dur", fmt_s(max(0.018, old_dur * scale)))

    ambient = tagline_window(events, duration)
    tagline_start = ambient["tagline_start"]
    tagline_end = ambient["tagline_end"]
    tagline_mask = by_id("alius-tagline-reveal")
    width_anim = None
    if tagline_mask is not None:
        width_anim = next(
            (
                child
                for child in tagline_mask.iter()
                if local_name(child.tag) == "animate" and child.attrib.get("attributeName") == "width"
            ),
            None,
        )
    tagline_visible_fraction = first_positive_key_fraction(width_anim)
    remaining_fraction = max(0.05, 1.0 - tagline_visible_fraction)
    tagline_dur = max(0.65, (tagline_end - tagline_start) / remaining_fraction)
    tagline_begin = tagline_start - tagline_visible_fraction * tagline_dur
    tagline = by_id("alius-tagline")
    if tagline is not None:
        tagline.set("opacity", "0")
        for anim in [child for child in tagline if local_name(child.tag) == "animate" and child.attrib.get("attributeName") == "opacity"]:
            anim.set("begin", fmt_s(tagline_begin))
            anim.set("dur", fmt_s(tagline_dur))
            anim.set("fill", "freeze")
    if tagline_mask is not None:
        for anim in [child for child in tagline_mask.iter() if local_name(child.tag) == "animate" and child.attrib.get("attributeName") == "width"]:
            anim.set("begin", fmt_s(tagline_begin))
            anim.set("dur", fmt_s(tagline_dur))
            anim.set("fill", "freeze")
        for anim in [child for child in tagline_mask.iter() if local_name(child.tag) == "animateTransform"]:
            anim.set("begin", fmt_s(tagline_begin))
            anim.set("dur", fmt_s(tagline_dur))
            anim.set("fill", "freeze")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=False)


def extract_accent(audio: np.ndarray, peak_time: float, duration: float = 0.36) -> np.ndarray:
    start = max(0, int((peak_time - 0.045) * SAMPLE_RATE))
    length = max(1, int(duration * SAMPLE_RATE))
    snippet = audio[start : start + length].copy()
    if snippet.size < length:
        snippet = np.pad(snippet, (0, length - snippet.size))
    fade = max(1, int(0.025 * SAMPLE_RATE))
    snippet[:fade] *= np.linspace(0.0, 1.0, fade)
    snippet[-fade:] *= np.linspace(1.0, 0.0, fade)
    peak = float(np.max(np.abs(snippet))) if snippet.size else 0.0
    if peak > 1e-5:
        snippet *= 0.85 / peak
    return snippet


def make_mixed_audio(
    track: Track,
    base_audio: np.ndarray,
    events: dict[str, float],
    accent_pool: list[tuple[int, str, np.ndarray]],
) -> tuple[np.ndarray, list[dict[str, object]]]:
    mixed = base_audio.astype(np.float32).copy()
    overlays: list[dict[str, object]] = []
    is_short = track.duration < 6.8
    sparse = False
    accent_events = ["A", "L", "I", "U", "S"] if is_short else []
    if track.duration < 5.4:
        accent_events = ["left_leaf", "right_leaf", "A", "L", "I", "U", "S"]
    if sparse and not accent_events:
        accent_events = ["A", "I", "S"]
    if not accent_events or not accent_pool:
        return mixed, overlays

    for idx, event_name in enumerate(accent_events):
        source_number, source_name, accent = accent_pool[(track.number + idx * 3) % len(accent_pool)]
        start = max(0, int((events[event_name] - 0.045) * SAMPLE_RATE))
        end = min(mixed.size, start + accent.size)
        if end <= start:
            continue
        gain = 0.16 if track.duration >= 5.4 else 0.20
        mixed[start:end] += accent[: end - start] * gain
        overlays.append(
            {
                "event": event_name,
                "time": events[event_name],
                "source_track": source_number,
                "source_name": source_name,
                "gain": gain,
            }
        )
    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 0.98:
        mixed *= 0.98 / peak
    return mixed, overlays


def select_spaced_peaks(
    peaks: list[dict[str, float]],
    *,
    count: int,
    low: float,
    high: float,
    min_gap: float,
    chronological: bool,
) -> list[dict[str, float]]:
    candidates = [peak for peak in peaks if low <= float(peak["time"]) <= high]
    if chronological:
        selected: list[dict[str, float]] = []
        for peak in candidates:
            if all(abs(float(peak["time"]) - float(existing["time"])) >= min_gap for existing in selected):
                selected.append(peak)
            if len(selected) >= count:
                return selected
    else:
        selected = []
        for peak in sorted(candidates, key=lambda item: float(item["score"]), reverse=True):
            if all(abs(float(peak["time"]) - float(existing["time"])) >= min_gap for existing in selected):
                selected.append(peak)
            if len(selected) >= count:
                break
        selected.sort(key=lambda item: float(item["time"]))
        if len(selected) >= count:
            return selected

    used_times = [float(peak["time"]) for peak in selected]
    fallback = np.linspace(low, high, count)
    for time in fallback:
        if len(selected) >= count:
            break
        if all(abs(float(time) - existing) >= min_gap * 0.72 for existing in used_times):
            selected.append({"time": round(float(time), 4), "score": 0.02})
            used_times.append(float(time))
    selected.sort(key=lambda item: float(item["time"]))
    return selected[:count]


def score_cue_sequence(cues: list[dict[str, float]], *, count: int, target_gap: float, target_span: float) -> float:
    if len(cues) < count:
        return 0.0
    scores = [float(cue["score"]) for cue in cues[:count]]
    times = [float(cue["time"]) for cue in cues[:count]]
    gaps = [b - a for a, b in zip(times, times[1:])]
    avg_score = min(1.0, sum(scores) / max(1, len(scores)))
    avg_gap = sum(gaps) / max(1, len(gaps))
    gap_score = max(0.0, 1.0 - abs(avg_gap - target_gap) / max(0.001, target_gap))
    regularity = max(0.0, 1.0 - float(np.std(gaps)) / max(0.001, target_gap * 1.45))
    span = times[-1] - times[0]
    span_score = max(0.0, 1.0 - abs(span - target_span) / max(0.001, target_span))
    fallback_penalty = sum(1 for score in scores if score <= 0.03) / count
    return max(0.0, avg_score * 0.55 + gap_score * 0.16 + regularity * 0.14 + span_score * 0.15 - fallback_penalty * 0.45)


def build_cue_profiles(tracks: list[Track], analyses: dict[int, dict[str, object]]) -> list[CueProfile]:
    profiles: list[CueProfile] = []
    for track in tracks:
        peaks = analyses[track.number]["peaks"]
        leaf_low = min(0.42, max(0.24, track.duration * 0.045))
        leaf_high = min(2.25, max(leaf_low + 0.72, track.duration * 0.38))
        leaf_cues = select_spaced_peaks(
            peaks,
            count=3,
            low=leaf_low,
            high=leaf_high,
            min_gap=0.16,
            chronological=True,
        )
        word_low = max(0.78, track.duration * 0.18)
        word_high = max(word_low + 1.2, track.duration - 0.36)
        word_cues = select_spaced_peaks(
            peaks,
            count=5,
            low=word_low,
            high=word_high,
            min_gap=0.22,
            chronological=False,
        )
        profiles.append(
            CueProfile(
                track=track,
                peaks=peaks,
                leaf_cues=leaf_cues,
                word_cues=word_cues,
                leaf_score=score_cue_sequence(leaf_cues, count=3, target_gap=0.31, target_span=0.68),
                word_score=score_cue_sequence(word_cues, count=5, target_gap=0.55, target_span=2.35),
            )
        )
    return profiles


def rms_segment(audio: np.ndarray, start: float, end: float, sr: int = SAMPLE_RATE) -> float:
    a = max(0, min(audio.size, int(start * sr)))
    b = max(a + 1, min(audio.size, int(end * sr)))
    segment = audio[a:b]
    return float(np.sqrt(np.mean(segment * segment))) if segment.size else 0.0


def transition_compatibility(leaf: CueProfile, word: CueProfile, decoded: dict[int, np.ndarray]) -> float:
    leaf_audio = decoded[leaf.track.number]
    word_audio = decoded[word.track.number]
    leaf_last = float(leaf.leaf_cues[-1]["time"])
    word_first = float(word.word_cues[0]["time"])
    leaf_energy = rms_segment(leaf_audio, leaf_last - 0.28, leaf_last + 0.42)
    word_energy = rms_segment(word_audio, word_first - 0.42, word_first + 0.32)
    ratio = math.log((word_energy + 1e-5) / (leaf_energy + 1e-5))
    energy_score = max(0.0, 1.0 - abs(ratio) / 1.65)
    leaf_span = float(leaf.leaf_cues[-1]["time"]) - float(leaf.leaf_cues[0]["time"])
    word_span = float(word.word_cues[-1]["time"]) - float(word.word_cues[0]["time"])
    pacing_score = max(0.0, 1.0 - abs((word_span / max(0.1, leaf_span)) - 3.4) / 3.4)
    return energy_score * 0.72 + pacing_score * 0.28


def select_composite_pairs(
    profiles: list[CueProfile],
    decoded: dict[int, np.ndarray],
    count: int,
    fixed_leaf_track: int | None = None,
) -> list[CompositePair]:
    raw: list[tuple[float, float, CueProfile, CueProfile]] = []
    for leaf in profiles:
        if fixed_leaf_track is not None and leaf.track.number != fixed_leaf_track:
            continue
        if leaf.leaf_score <= 0:
            continue
        for word in profiles:
            if leaf.track.number == word.track.number or word.word_score <= 0:
                continue
            transition_score = transition_compatibility(leaf, word, decoded)
            score = leaf.leaf_score * 0.42 + word.word_score * 0.48 + transition_score * 0.10
            raw.append((score, transition_score, leaf, word))
    raw.sort(key=lambda item: item[0], reverse=True)

    selected: list[CompositePair] = []
    seen: set[tuple[int, int]] = set()
    leaf_use: Counter[int] = Counter()
    word_use: Counter[int] = Counter()
    for cap in [4, 5, 6, 8, 40]:
        for score, transition_score, leaf, word in raw:
            key = (leaf.track.number, word.track.number)
            if key in seen:
                continue
            if leaf_use[leaf.track.number] >= cap or word_use[word.track.number] >= cap:
                continue
            seen.add(key)
            leaf_use[leaf.track.number] += 1
            word_use[word.track.number] += 1
            selected.append(CompositePair(len(selected) + 1, leaf, word, score, transition_score))
            if len(selected) >= count:
                return selected
    if len(selected) < count:
        raise RuntimeError(f"Only selected {len(selected)} composite pairs; needed {count}")
    return selected


def fade_in_place(audio: np.ndarray, start_sample: int, end_sample: int) -> None:
    start_sample = max(0, min(audio.size, start_sample))
    end_sample = max(start_sample, min(audio.size, end_sample))
    if end_sample <= start_sample:
        return
    audio[start_sample:end_sample] *= np.linspace(0.0, 1.0, end_sample - start_sample, dtype=np.float32)
    audio[:start_sample] = 0


def fade_out_in_place(audio: np.ndarray, start_sample: int, end_sample: int) -> None:
    start_sample = max(0, min(audio.size, start_sample))
    end_sample = max(start_sample, min(audio.size, end_sample))
    if end_sample <= start_sample:
        return
    audio[start_sample:end_sample] *= np.linspace(1.0, 0.0, end_sample - start_sample, dtype=np.float32)
    audio[end_sample:] = 0


def make_composite_audio_and_events(
    pair: CompositePair,
    decoded: dict[int, np.ndarray],
    *,
    hold_leaf_under_word: bool = False,
) -> tuple[np.ndarray, dict[str, float], dict[str, object]]:
    leaf_track = pair.leaf.track
    word_track = pair.word.track
    leaf_audio = decoded[leaf_track.number].astype(np.float32)
    word_audio = decoded[word_track.number].astype(np.float32)
    leaf_times = [float(cue["time"]) for cue in pair.leaf.leaf_cues[:3]]
    word_times = [float(cue["time"]) for cue in pair.word.word_cues[:5]]

    leaf_gaps = [b - a for a, b in zip(leaf_times, leaf_times[1:])]
    transition_gap = min(0.82, max(0.48, (sum(leaf_gaps) / max(1, len(leaf_gaps))) * 1.55))
    target_a = leaf_times[-1] + transition_gap
    word_lead_in = min(0.50, max(0.22, word_times[0]))
    word_trim = max(0.0, word_times[0] - word_lead_in)
    word_start = max(0.0, target_a - word_lead_in)
    word_shift = word_start - word_trim

    events = {
        "middle_leaf": round(leaf_times[0], 3),
        "left_leaf": round(leaf_times[1], 3),
        "right_leaf": round(leaf_times[2], 3),
    }
    for letter, cue_time in zip(["A", "L", "I", "U", "S"], word_times):
        events[letter] = round(cue_time + word_shift, 3)

    word_tail = min(2.25, max(1.05, word_track.duration - word_times[-1]))
    word_end = min(word_track.duration, word_times[-1] + word_tail)
    src_start = int(word_trim * SAMPLE_RATE)
    src_end = max(src_start + 1, int(word_end * SAMPLE_RATE))
    word_segment = word_audio[src_start:src_end].copy()
    if hold_leaf_under_word:
        leaf_take_end = min(leaf_track.duration, max(events["S"] + 0.95, events["A"] + 2.2, leaf_times[-1] + 2.45))
    else:
        leaf_take_end = min(leaf_track.duration, max(events["A"] + 0.35, leaf_times[-1] + 0.95))
    leaf_segment = leaf_audio[: max(1, int(leaf_take_end * SAMPLE_RATE))].copy()

    composite_duration = max(events["S"] + 0.92, word_start + word_segment.size / SAMPLE_RATE, leaf_take_end + 0.25)
    total_samples = max(2, int(math.ceil(composite_duration * SAMPLE_RATE)))
    mixed = np.zeros(total_samples, dtype=np.float32)

    if hold_leaf_under_word:
        leaf_fade_start = max(events["A"] + 0.30, events["U"] - 0.15)
        leaf_fade_end = min(leaf_take_end, max(events["S"] + 0.80, leaf_fade_start + 0.70))
    else:
        leaf_fade_start = max(0.0, leaf_times[-1] + 0.12)
        leaf_fade_end = max(leaf_times[-1] + 0.42, events["A"] + 0.10)
    fade_start = int(leaf_fade_start * SAMPLE_RATE)
    fade_end = int(leaf_fade_end * SAMPLE_RATE)
    fade_out_in_place(leaf_segment, fade_start, fade_end)
    leaf_gain = 0.74 if hold_leaf_under_word else 0.86
    mixed[: min(mixed.size, leaf_segment.size)] += leaf_segment[: min(mixed.size, leaf_segment.size)] * leaf_gain

    word_fade = min(0.70 if hold_leaf_under_word else 0.55, max(0.24, events["A"] - word_start + 0.04))
    fade_in_place(word_segment, 0, int(word_fade * SAMPLE_RATE))
    fade_out_in_place(word_segment, max(0, word_segment.size - int(0.55 * SAMPLE_RATE)), word_segment.size)
    leaf_rms = rms_segment(leaf_audio, leaf_times[0], leaf_times[-1] + 0.35)
    word_rms = rms_segment(word_audio, word_times[0], min(word_track.duration, word_times[-1] + 0.35))
    gain_base = 0.76 if hold_leaf_under_word else 0.86
    word_gain = min(1.35, max(0.58, gain_base * (leaf_rms / (word_rms + 1e-5))))
    dest = int(word_start * SAMPLE_RATE)
    end = min(mixed.size, dest + word_segment.size)
    if end > dest:
        mixed[dest:end] += word_segment[: end - dest] * word_gain

    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 0.98:
        mixed *= 0.98 / peak
    events["settle"] = round(min(composite_duration - 0.08, max(events["S"] + 0.30, composite_duration - 0.42)), 3)
    if events["settle"] <= events["S"]:
        events["settle"] = round(min(composite_duration - 0.04, events["S"] + 0.18), 3)

    metadata = {
        "leaf_cues_source_seconds": [round(value, 4) for value in leaf_times],
        "word_cues_source_seconds": [round(value, 4) for value in word_times],
        "word_source_trim_seconds": round(word_trim, 4),
        "word_start_seconds": round(word_start, 4),
        "word_shift_seconds": round(word_shift, 4),
        "transition_gap_seconds": round(transition_gap, 4),
        "crossfade": {
            "leaf_fade_start": round(fade_start / SAMPLE_RATE, 4),
            "leaf_fade_end": round(fade_end / SAMPLE_RATE, 4),
            "word_fade_in_duration": round(word_fade, 4),
        },
        "leaf_gain": leaf_gain,
        "word_gain": round(word_gain, 4),
        "hold_leaf_under_word": hold_leaf_under_word,
    }
    return mixed, events, metadata


def svg_to_html(svg_text: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #ffffff;
    }}
    svg {{
      width: 100vw;
      height: 100vh;
      display: block;
    }}
  </style>
</head>
<body>
{svg_text}
</body>
</html>"""


def render_frames(page, svg_path: Path, frame_dir: Path, duration: float) -> int:
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("*.png"):
        old.unlink()
    html = svg_to_html(svg_path.read_text(encoding="utf-8"))
    page.set_content(html, wait_until="load")
    page.evaluate(
        """() => {
            const svg = document.querySelector('svg');
            svg.pauseAnimations();
            svg.setCurrentTime(0);
        }"""
    )
    frame_count = max(2, int(math.ceil(duration * FPS)))
    for frame in range(frame_count):
        t = min(duration, frame / FPS)
        page.evaluate(
            """(time) => {
                const svg = document.querySelector('svg');
                svg.pauseAnimations();
                svg.setCurrentTime(time);
            }""",
            t,
        )
        page.screenshot(path=str(frame_dir / f"{frame:05d}.png"), full_page=False)
    return frame_count


def encode_video(ffmpeg: str, frame_dir: Path, audio_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out_path.with_suffix(".tmp.mp4")
    if tmp_out.exists():
        tmp_out.unlink()
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-framerate",
            str(FPS),
            "-i",
            str(frame_dir / "%05d.png"),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(tmp_out),
        ]
    )
    tmp_out.replace(out_path)


def make_contact_sheet(samples: list[tuple[str, Path]], out_path: Path) -> None:
    if not samples:
        return
    thumbs = []
    for label, path in samples:
        img = Image.open(path).convert("RGB")
        img.thumbnail((357, 173))
        canvas = Image.new("RGB", (357, 203), "white")
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 180), label, fill=(32, 48, 32))
        thumbs.append(canvas)
    cols = 3
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 357, rows * 203), "white")
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * 357, (idx // cols) * 203))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def write_source_note(out: Path, audio_dir: Path, extra: str = "") -> None:
    body = (
        "Audio source folder: "
        + str(audio_dir)
        + os.linesep
        + "These files are treated as user-provided local source audio. Confirm the license before public release."
        + os.linesep
    )
    if extra:
        body += extra + os.linesep
    (out / "SOURCE-LICENSE-NOTE.txt").write_text(body, encoding="utf-8")


def run_composite_batch(
    args: argparse.Namespace,
    tracks: list[Track],
    decoded: dict[int, np.ndarray],
    analyses: dict[int, dict[str, object]],
    dirs: dict[str, Path],
    ffmpeg: str,
) -> list[dict[str, object]]:
    profiles = build_cue_profiles(tracks, analyses)
    max_pairs = len(tracks) - 1 if args.fixed_leaf_track else args.composite_count
    pair_count = min(args.composite_count, max_pairs)
    if args.limit:
        pair_count = min(args.limit, pair_count)
    pairs = select_composite_pairs(profiles, decoded, pair_count, fixed_leaf_track=args.fixed_leaf_track)
    (args.output / "pair-ranking.json").write_text(
        json.dumps(
            [
                {
                    "rank": idx + 1,
                    "leaf_track": pair.leaf.track.number,
                    "leaf_name": pair.leaf.track.name,
                    "word_track": pair.word.track.number,
                    "word_name": pair.word.track.name,
                    "score": round(pair.score, 4),
                    "transition_score": round(pair.transition_score, 4),
                    "leaf_score": round(pair.leaf.leaf_score, 4),
                    "word_score": round(pair.word.word_score, 4),
                }
                for idx, pair in enumerate(pairs)
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest: list[dict[str, object]] = []
    contact_samples: list[tuple[str, Path]] = []
    sample_indices = {1, 2, 15, 31, 35, 40}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        for index, pair in enumerate(pairs, start=1):
            basename = f"{index:02d}-{pair.leaf.track.slug}__{pair.word.track.slug}"
            audio_out = dirs["audio"] / f"{basename}.wav"
            svg_out = dirs["svg"] / f"{basename}.svg"
            video_out = dirs["video"] / f"{basename}.mp4"
            analysis_out = dirs["analysis"] / f"{basename}-events.json"
            frame_dir = dirs["frames"] / basename

            mixed, events, composite_meta = make_composite_audio_and_events(
                pair,
                decoded,
                hold_leaf_under_word=args.hold_leaf_under_word,
            )
            duration = mixed.size / SAMPLE_RATE
            write_wav(audio_out, mixed)
            retime_svg(args.template, svg_out, events, duration)
            frame_count = render_frames(page, svg_out, frame_dir, duration)
            encode_video(ffmpeg, frame_dir, audio_out, video_out)

            sample_frame = frame_dir / f"{max(0, frame_count - 1):05d}.png"
            if index in sample_indices and sample_frame.exists():
                sample_copy = dirs["contact"] / f"{basename}-final.png"
                shutil.copyfile(sample_frame, sample_copy)
                contact_samples.append((basename, sample_copy))
            if not args.keep_frames:
                clean_dir(frame_dir)

            payload = {
                "variant": index,
                "name": basename,
                "duration": round(duration, 3),
                "pair_score": round(pair.score, 4),
                "transition_score": round(pair.transition_score, 4),
                "leaf_source": {
                    "number": pair.leaf.track.number,
                    "name": pair.leaf.track.name,
                    "path": str(pair.leaf.track.path),
                    "duration": round(pair.leaf.track.duration, 3),
                    "score": round(pair.leaf.leaf_score, 4),
                },
                "word_source": {
                    "number": pair.word.track.number,
                    "name": pair.word.track.name,
                    "path": str(pair.word.track.path),
                    "duration": round(pair.word.track.duration, 3),
                    "score": round(pair.word.word_score, 4),
                },
                "events": events,
                "ambient_events": tagline_window(events, duration),
                "composite": composite_meta,
                "leaf_peaks": pair.leaf.peaks[:20],
                "word_peaks": pair.word.peaks[:20],
                "files": {
                    "audio": str(audio_out),
                    "svg": str(svg_out),
                    "video": str(video_out),
                },
            }
            analysis_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            manifest.append(payload)
            print(
                f"[{index:02d}/{len(pairs):02d}] "
                f"{pair.leaf.track.slug} + {pair.word.track.slug}: {frame_count} frames -> {video_out.name}"
            )
        browser.close()
    make_contact_sheet(contact_samples, dirs["contact"] / "representative-final-frames.jpg")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--keep-frames", action="store_true")
    parser.add_argument("--composite-best-pairs", action="store_true")
    parser.add_argument("--composite-count", type=int, default=40)
    parser.add_argument("--fixed-leaf-track", type=int, default=0)
    parser.add_argument("--hold-leaf-under-word", action="store_true")
    args = parser.parse_args()
    args.fixed_leaf_track = args.fixed_leaf_track or None

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    all_tracks = list_tracks(args.audio_dir, ffprobe)
    if len(all_tracks) != 40:
        raise RuntimeError(f"Expected 40 audio files, found {len(all_tracks)} in {args.audio_dir}")
    tracks = all_tracks if args.composite_best_pairs else all_tracks[: args.limit] if args.limit else all_tracks

    out = args.output
    dirs = {
        "video": out / "video",
        "audio": out / ("audio-composite" if args.composite_best_pairs else "audio-mix"),
        "svg": out / "svg",
        "analysis": out / "analysis",
        "frames": out / "frames",
        "contact": out / "contact-sheet",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    decoded: dict[int, np.ndarray] = {}
    analyses: dict[int, dict[str, object]] = {}
    print(f"Analyzing {len(tracks)} tracks...")
    for track in tracks:
        audio = decode_audio(ffmpeg, track.path)
        decoded[track.number] = audio
        peaks = detect_peaks(audio, track.duration)
        events = choose_event_times(peaks, track.duration)
        analyses[track.number] = {"peaks": peaks, "events": events}

    if args.composite_best_pairs:
        manifest = run_composite_batch(args, tracks, decoded, analyses, dirs, ffmpeg)
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_source_note(
            out,
            args.audio_dir,
            "Composite batch: each MP4 combines one leaf-cue source with a distinct word-cue source via crossfade.",
        )
        print(f"Done. Videos: {dirs['video']}")
        return 0

    accent_pool: list[tuple[int, str, np.ndarray]] = []
    for track in tracks:
        if track.duration <= 6.9:
            peaks = analyses[track.number]["peaks"]
            peak_time = peaks[0]["time"] if peaks else 0.08
            for peak in peaks:
                if peak["time"] > 0.10:
                    peak_time = peak["time"]
                    break
            accent_pool.append((track.number, track.name, extract_accent(decoded[track.number], float(peak_time))))

    manifest: list[dict[str, object]] = []
    contact_samples: list[tuple[str, Path]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        for index, track in enumerate(tracks, start=1):
            analysis = analyses[track.number]
            events = analysis["events"]
            mixed, overlays = make_mixed_audio(track, decoded[track.number], events, accent_pool)
            audio_out = dirs["audio"] / f"{track.slug}.wav"
            svg_out = dirs["svg"] / f"{track.slug}.svg"
            video_out = dirs["video"] / f"{track.slug}.mp4"
            analysis_out = dirs["analysis"] / f"{track.slug}-events.json"
            frame_dir = dirs["frames"] / track.slug

            write_wav(audio_out, mixed)
            retime_svg(args.template, svg_out, events, track.duration)
            frame_count = render_frames(page, svg_out, frame_dir, track.duration)
            encode_video(ffmpeg, frame_dir, audio_out, video_out)

            sample_frame = frame_dir / f"{max(0, frame_count - 1):05d}.png"
            if track.number in {1, 2, 15, 31, 35, 40} and sample_frame.exists():
                sample_copy = dirs["contact"] / f"{track.slug}-final.png"
                shutil.copyfile(sample_frame, sample_copy)
                contact_samples.append((track.slug, sample_copy))
            if not args.keep_frames:
                clean_dir(frame_dir)

            payload = {
                "number": track.number,
                "name": track.name,
                "source": str(track.path),
                "duration": round(track.duration, 3),
                "events": events,
                "ambient_events": tagline_window(events, track.duration),
                "peaks": analysis["peaks"][:20],
                "accent_overlays": overlays,
                "files": {
                    "audio": str(audio_out),
                    "svg": str(svg_out),
                    "video": str(video_out),
                },
            }
            analysis_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            manifest.append(payload)
            print(f"[{index:02d}/{len(tracks):02d}] {track.slug}: {frame_count} frames -> {video_out.name}")
        browser.close()

    make_contact_sheet(contact_samples, dirs["contact"] / "representative-final-frames.jpg")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_source_note(out, args.audio_dir)
    print(f"Done. Videos: {dirs['video']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
