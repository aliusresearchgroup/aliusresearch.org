#!/usr/bin/env python3
"""Export ALIUS Bulletin Q&A transcript sidecars for the website."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import shutil


REPO = Path(__file__).resolve().parents[2]
DEFAULT_BULLETIN_REPO = REPO.parent / "ALIUS-bulletin"
SOURCE_OUT = "output/audio_interviews"
TARGET_REL = Path("media/audio/bulletin/transcripts")
AUDIO_TARGET_REL = Path("media/audio/bulletin/kokoro")

CARD_TO_INTERVIEW = {
    "bulletin-froese-irruption": "Issue07/Froese_Koroma",
    "bulletin-gonzalez-interdisciplinary": "Issue06/Gonzalez_Koroma",
    "bulletin-sapolsky-free-will": "Issue06/Sapolsky_Mikhailova_Friedman",
    "bulletin-doss-cinco-sins": "Issue06/Doss_Fejer",
    "bulletin-skipper-language": "Issue06/Skipper_Roseman_Koroma_Fejer",
    "bulletin-canna-seligman-culture": "Issue05/Canna_Seligman_Koroma",
    "bulletin-chadha-indian-philosophy": "Issue05/Chadha_Aviles_Koroma",
    "bulletin-olson-yaden-therapeutic-effects": "Issue05/Olson_Yaden_Fejer",
    "bulletin-schmidt-phenomenoconnectomics": "Issue05/Schmidt_Fejer",
    "bulletin-baird-lucid-dreaming": "Issue04/Baird_Koroma",
    "bulletin-carter-dimensions": "Issue04/Carter_Preller",
    "bulletin-gosseries-disorders": "Issue04/Gosseries_Martial",
    "bulletin-hanks-decision-making": "Issue04/Hanks_Mikhailova_Friedman",
    "bulletin-lenggenhager-bodily-self": "Issue04/Lenggenhager_Ho_Milliere",
    "bulletin-vignemont-body-self": "Issue04/Vignemont_Milliere_Serrahima",
    "bulletin-bayne-natural-phenomenon": "Issue03/Bayne_Bucci_Koroma",
    "bulletin-dennett-explained": "Issue03/Dennett_Fleig-Goldstein_Friedman",
    "bulletin-dienes-hypnosis-meditation": "Issue03/Dienes_Martin",
    "bulletin-preller-sociality": "Issue03/Preller_Dumas",
    "bulletin-winkelman-neuroanthropology": "Issue03/Winkelman_Fortier",
    "bulletin-fox-spontaneous-thinking": "Issue02/Fox_Koroma",
    "bulletin-friston-woodlice": "Issue02/Friston_Fortier_Friedman",
    "bulletin-metzinger-self-models": "Issue02/Metzinger_Limanowski_Milliere",
    "bulletin-david-nichols-pharmacology": "Issue02/Nichols_Roseman_Timmermann",
    "bulletin-oregan-sensorimotor": "Issue02/ORegan_Erickson-Davis",
    "bulletin-ratcliffe-hallucinations": "Issue02/Ratcliffe_Frerejouan",
    "bulletin-taves-religious-experience": "Issue02/Taves_Fortier_Canna",
    "bulletin-carhart-harris-psychedelics": "Issue01/Carhart-Harris_Fortier_Milliere",
    "bulletin-hohwy-conscious-modes": "Issue01/Hohwy_Koroma",
    "bulletin-luhrmann-anthropology-mind": "Issue01/Luhrmann_Fortier",
    "bulletin-mccarthy-jones-voice-hearing": "Issue01/McCarthy-Jones_Frerejouan",
    "bulletin-seligman-dissociative": "Issue01/Seligman_Halloy",
    "bulletin-windt-dreams": "Issue01/Windt_Bucci_Milliere",
}


def repair_mojibake(value: str) -> str:
    for _ in range(3):
        if not re.search(r"[ÃÂâ]", value):
            break
        try:
            repaired = value.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
        if repaired == value:
            break
        value = repaired
    return value


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", repair_mojibake(value)).strip()


def parse_transcript(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    question_speaker = re.search(r"^Question voice:\s*(.*?)\s*\(", text, re.M)
    answer_speaker = re.search(r"^Answer voice:\s*(.*?)\s*\(", text, re.M)
    body = re.search(
        r"QUESTION SPOKEN TEXT:\s*(?P<question>.*?)\s*ANSWER SPOKEN TEXT:\s*(?P<answer>.*)\s*$",
        text,
        re.S,
    )
    if not body:
        raise ValueError(f"Cannot parse transcript body: {path}")
    return {
        "question_speaker": clean_text(question_speaker.group(1)) if question_speaker else "",
        "answer_speaker": clean_text(answer_speaker.group(1)) if answer_speaker else "",
        "question": clean_text(body.group("question")),
        "answer": clean_text(body.group("answer")),
    }


def load_units(bulletin_repo: Path) -> dict[str, list[dict[str, object]]]:
    source_dir = bulletin_repo / SOURCE_OUT
    manifest_path = source_dir / "qa_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in manifest:
        interview_id = item["interview_id"]
        if interview_id.startswith("Fictional/"):
            continue
        transcript_path = bulletin_repo / item["transcript_path"]
        parsed = parse_transcript(transcript_path)
        grouped.setdefault(interview_id, []).append(
            {
                "unit": int(item["unit"]),
                "question_speaker": parsed["question_speaker"],
                "answer_speaker": parsed["answer_speaker"],
                "question": parsed["question"],
                "answer": parsed["answer"],
            }
        )
    for units in grouped.values():
        units.sort(key=lambda unit: int(unit["unit"]))
    return grouped


def transcript_text(card_id: str, interview_id: str, units: list[dict[str, object]]) -> str:
    lines = [
        f"ALIUS Bulletin transcript",
        f"Card: {card_id}",
        f"Source: {interview_id}",
        f"Q&A units: {len(units)}",
        "",
    ]
    for unit in units:
        lines.extend(
            [
                f"Q&A {int(unit['unit']):03d}",
                f"{unit['question_speaker']}: {unit['question']}",
                "",
                f"{unit['answer_speaker']}: {unit['answer']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def parse_chapters(path: Path) -> list[dict[str, object]]:
    chapters: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                unit = int(row["chapter"])
                start_ms = int(row["start_ms"])
                end_ms = int(row["end_ms"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Cannot parse chapter row in {path}: {row}") from exc
            chapters.append(
                {
                    "unit": unit,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": max(0, end_ms - start_ms),
                    "title": clean_text(row.get("title", "")) or f"Q&A {unit:03d}",
                }
            )
    return chapters


def attach_audio_metadata(records: dict[str, dict[str, object]], bulletin_repo: Path) -> None:
    source_dir = bulletin_repo / SOURCE_OUT
    for record in records.values():
        interview_id = str(record["source_interview_id"])
        interview_dir = source_dir / Path(*interview_id.split("/"))
        mp3_path = interview_dir / "interview.mp3"
        chapters_path = interview_dir / "interview_chapters.csv"
        if not mp3_path.exists():
            raise FileNotFoundError(f"Missing Kokoro interview MP3: {mp3_path}")
        if not chapters_path.exists():
            raise FileNotFoundError(f"Missing Kokoro chapter CSV: {chapters_path}")
        public_base = f"/{AUDIO_TARGET_REL.as_posix()}/{interview_id}"
        chapters = parse_chapters(chapters_path)
        record["audio"] = f"{public_base}/interview.mp3"
        record["audio_download"] = f"{public_base}/interview.mp3"
        record["audio_source"] = "kokoro-transcript"
        record["audio_chapter_count"] = len(chapters)
        record["audio_chapters"] = chapters


def copy_audio_targets(records: dict[str, dict[str, object]], bulletin_repo: Path, audio_root: Path) -> None:
    source_dir = bulletin_repo / SOURCE_OUT
    audio_root.mkdir(parents=True, exist_ok=True)
    for record in records.values():
        interview_id = str(record["source_interview_id"])
        source_mp3 = source_dir / Path(*interview_id.split("/")) / "interview.mp3"
        target_dir = audio_root / Path(*interview_id.split("/"))
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_mp3, target_dir / "interview.mp3")
        (target_dir / "interview_chapters.json").write_text(
            json.dumps(record["audio_chapters"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def write_targets(records: dict[str, dict[str, object]], target_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    for old in target_root.glob("*"):
        if old.is_file() and old.suffix in {".json", ".txt"}:
            old.unlink()

    index: dict[str, dict[str, object]] = {}
    for card_id, record in records.items():
        json_name = f"{card_id}.json"
        text_name = f"{card_id}.txt"
        (target_root / json_name).write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        (target_root / text_name).write_text(
            transcript_text(card_id, str(record["source_interview_id"]), list(record["units"])),
            encoding="utf-8",
        )
        index[card_id] = {
            "src": f"/{TARGET_REL.as_posix()}/{json_name}",
            "download": f"/{TARGET_REL.as_posix()}/{text_name}",
            "unit_count": record["unit_count"],
            "source_interview_id": record["source_interview_id"],
            "audio": record.get("audio", ""),
            "audio_download": record.get("audio_download", ""),
            "audio_source": record.get("audio_source", ""),
            "audio_chapter_count": record.get("audio_chapter_count", 0),
            "audio_chapters": record.get("audio_chapters", []),
        }
    (target_root / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulletin-repo", type=Path, default=DEFAULT_BULLETIN_REPO)
    parser.add_argument("--site-root", type=Path, default=REPO)
    args = parser.parse_args()

    grouped = load_units(args.bulletin_repo)
    missing = sorted(set(CARD_TO_INTERVIEW.values()) - set(grouped))
    if missing:
        raise RuntimeError("Missing transcript groups: " + ", ".join(missing))

    records: dict[str, dict[str, object]] = {}
    for card_id, interview_id in CARD_TO_INTERVIEW.items():
        units = grouped[interview_id]
        records[card_id] = {
            "card_id": card_id,
            "source_project": str(args.bulletin_repo),
            "source_script": "AI-agents/generate_interview_audio_kokoro.py",
            "source_interview_id": interview_id,
            "unit_count": len(units),
            "units": units,
        }
    attach_audio_metadata(records, args.bulletin_repo)

    static_target = args.site_root / "site-src" / "static" / TARGET_REL
    docs_target = args.site_root / "docs" / TARGET_REL
    static_audio_target = args.site_root / "site-src" / "static" / AUDIO_TARGET_REL
    docs_audio_target = args.site_root / "docs" / AUDIO_TARGET_REL
    write_targets(records, static_target)
    copy_audio_targets(records, args.bulletin_repo, static_audio_target)
    if docs_target.exists():
        shutil.rmtree(docs_target)
    shutil.copytree(static_target, docs_target)
    if docs_audio_target.exists():
        shutil.rmtree(docs_audio_target)
    shutil.copytree(static_audio_target, docs_audio_target)

    print(f"Exported {len(records)} transcript sidecars")
    print(f"Exported {len(records)} Kokoro interview MP3s")
    print(f"Source: {args.bulletin_repo / SOURCE_OUT}")
    print(f"Static: {static_target}")
    print(f"Static audio: {static_audio_target}")
    print(f"Docs: {docs_target}")
    print(f"Docs audio: {docs_audio_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
