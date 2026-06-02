#!/usr/bin/env python3
"""Export generated Kokoro interview audio files for the website."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


REPO = Path(__file__).resolve().parents[2]
DEFAULT_BULLETIN_REPO = REPO.parent / "ALIUS-bulletin"
SOURCE_OUT = "output/audio_interviews"
TARGET_REL = Path("media/audio/bulletin/kokoro")

CARD_TO_INTERVIEW = {
    "bulletin-carhart-harris-psychedelics": "Issue01/Carhart-Harris_Fortier_Milliere",
    "bulletin-hohwy-conscious-modes": "Issue01/Hohwy_Koroma",
    "bulletin-luhrmann-anthropology-mind": "Issue01/Luhrmann_Fortier",
    "bulletin-mccarthy-jones-voice-hearing": "Issue01/McCarthy-Jones_Frerejouan",
    "bulletin-seligman-dissociative": "Issue01/Seligman_Halloy",
    "bulletin-windt-dreams": "Issue01/Windt_Bucci_Milliere",
    "bulletin-fox-spontaneous-thinking": "Issue02/Fox_Koroma",
    "bulletin-baird-lucid-dreaming": "Issue04/Baird_Koroma",
    "bulletin-carter-dimensions": "Issue04/Carter_Preller",
    "bulletin-gosseries-disorders": "Issue04/Gosseries_Martial",
    "bulletin-hanks-decision-making": "Issue04/Hanks_Mikhailova_Friedman",
    "bulletin-lenggenhager-bodily-self": "Issue04/Lenggenhager_Ho_Milliere",
    "bulletin-vignemont-body-self": "Issue04/Vignemont_Milliere_Serrahima",
}


def export_audio(bulletin_repo: Path, target_root: Path) -> list[tuple[str, Path, int]]:
    source_root = bulletin_repo / SOURCE_OUT
    target_root.mkdir(parents=True, exist_ok=True)
    for old in target_root.glob("*.mp3"):
        old.unlink()

    copied: list[tuple[str, Path, int]] = []
    for card_id, interview_id in CARD_TO_INTERVIEW.items():
        source = source_root / interview_id / "interview.mp3"
        if not source.exists():
            raise FileNotFoundError(f"Missing generated interview audio: {source}")
        target = target_root / f"{card_id}.mp3"
        shutil.copy2(source, target)
        copied.append((card_id, target, target.stat().st_size))
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulletin-repo", type=Path, default=DEFAULT_BULLETIN_REPO)
    parser.add_argument("--site-root", type=Path, default=REPO)
    args = parser.parse_args()

    static_target = args.site_root / "site-src" / "static" / TARGET_REL
    docs_target = args.site_root / "docs" / TARGET_REL

    copied = export_audio(args.bulletin_repo, static_target)
    if docs_target.exists():
        shutil.rmtree(docs_target)
    shutil.copytree(static_target, docs_target)

    print(f"Exported {len(copied)} generated interview audio files")
    print(f"Source: {args.bulletin_repo / SOURCE_OUT}")
    print(f"Static: {static_target}")
    print(f"Docs: {docs_target}")
    for card_id, target, size in copied:
        print(f"{card_id}\t{target.name}\t{size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
