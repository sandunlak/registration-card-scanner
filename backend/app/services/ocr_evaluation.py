"""Local-only CER/WER evaluation; input manifest and card files must be untracked."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

from app.schemas.ocr import HandwritingRegion
from app.services.ocr_service import create_ocr_pipeline

logger = logging.getLogger(__name__)


def edit_distance(left: str | Sequence[str], right: str | Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[right_index - 1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def normalize_transcription(value: str) -> str:
    return " ".join(value.casefold().split())


def transcription_errors(reference: str, prediction: str) -> tuple[int, int, int, int]:
    expected = normalize_transcription(reference)
    actual = normalize_transcription(prediction)
    expected_words = expected.split()
    actual_words = actual.split()
    return (
        edit_distance(expected, actual),
        len(expected),
        edit_distance(expected_words, actual_words),
        len(expected_words),
    )


def _process_memory_mb() -> float | None:
    """Return current process RSS in megabytes, or None if unavailable."""
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        pass
    # Fallback for Windows without psutil
    try:
        import ctypes
        import ctypes.wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetCurrentProcess()
        psapi = ctypes.windll.psapi  # type: ignore[attr-defined]
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return None


def _metrics(
    cases: list[dict[str, Any]],
    recognize: Callable[[dict[str, Any]], tuple[str, float]],
) -> dict[str, Any]:
    groups: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {
            "char_errors": 0,
            "characters": 0,
            "word_errors": 0,
            "words": 0,
            "exact_matches": 0,
            "elapsed_ms": 0,
            "cases": 0,
            "failures": 0,
        }
    )
    memory_before_mb = _process_memory_mb()
    peak_memory_mb: float | None = None

    for case in cases:
        key = (
            str(case["card_format"]),
            str(case["kind"]),
            str(case["category"]),
            str(case["condition"]),
        )
        group = groups[key]
        try:
            prediction, elapsed_ms = recognize(case)
        except Exception:
            logger.warning(
                "Evaluation case failed (format=%s kind=%s category=%s condition=%s)",
                *key,
            )
            group["failures"] += 1
            group["cases"] += 1
            continue

        char_errors, characters, word_errors, words = transcription_errors(
            str(case["reference"]), prediction
        )
        is_exact = normalize_transcription(str(case["reference"])) == normalize_transcription(
            prediction
        )
        group["char_errors"] += char_errors
        group["characters"] += characters
        group["word_errors"] += word_errors
        group["words"] += words
        group["exact_matches"] += int(is_exact)
        group["elapsed_ms"] += elapsed_ms
        group["cases"] += 1

        current_memory = _process_memory_mb()
        if current_memory is not None:
            if peak_memory_mb is None or current_memory > peak_memory_mb:
                peak_memory_mb = current_memory

    memory_after_mb = _process_memory_mb()

    total_cases = sum(int(values["cases"]) for values in groups.values())
    total_failures = sum(int(values["failures"]) for values in groups.values())
    total_exact = sum(int(values["exact_matches"]) for values in groups.values())
    successful = total_cases - total_failures

    result: dict[str, Any] = {
        "groups": [
            {
                "kind": kind,
                "card_format": card_format,
                "category": category,
                "condition": condition,
                "cases": int(values["cases"]),
                "failures": int(values["failures"]),
                "cer": values["char_errors"] / max(values["characters"], 1),
                "wer": values["word_errors"] / max(values["words"], 1),
                "exact_match_rate": (
                    values["exact_matches"] / max(values["cases"] - values["failures"], 1)
                ),
                "mean_inference_ms": values["elapsed_ms"] / max(values["cases"] - values["failures"], 1),
            }
            for (card_format, kind, category, condition), values in sorted(groups.items())
        ],
        "summary": {
            "total_cases": total_cases,
            "successful": successful,
            "failures": total_failures,
            "exact_match_rate": total_exact / max(successful, 1),
        },
        "memory": {},
        "note": "Aggregated metrics only; transcripts and file names are not emitted.",
    }

    if memory_before_mb is not None and memory_after_mb is not None:
        result["memory"] = {
            "before_mb": round(memory_before_mb, 1),
            "after_mb": round(memory_after_mb, 1),
            "delta_mb": round(memory_after_mb - memory_before_mb, 1),
        }
        if peak_memory_mb is not None:
            result["memory"]["peak_mb"] = round(peak_memory_mb, 1)

    # Preserve backward-compatible key
    result["total_cases"] = total_cases
    return result


def evaluate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation manifest must contain a non-empty cases array.")
    base_dir = manifest_path.parent.resolve()
    pipeline = create_ocr_pipeline()

    def recognize(case: dict[str, Any]) -> tuple[str, float]:
        image_path = Path(case["image_path"])
        if not image_path.is_absolute():
            image_path = base_dir / image_path
        regions = [HandwritingRegion.model_validate(case["handwriting_region"])] if case.get("handwriting_region") else []
        started = time.perf_counter()
        recognized, _, _ = pipeline.recognize(image_path, regions)
        selected = [region for region in recognized if region.recognition_type == case["kind"]]
        return " ".join(region.text for region in selected), (time.perf_counter() - started) * 1000

    return _metrics(cases, recognize)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local OCR evaluation without printing recognized text.")
    parser.add_argument("manifest", type=Path, help="Path to a private, untracked JSON reference manifest.")
    parser.add_argument("--output", type=Path, help="Optional metrics-only JSON report output path.")
    args = parser.parse_args()
    report = evaluate_manifest(args.manifest)
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Aggregate evaluation metrics written to {args.output}.")
    else:
        print(serialized)


if __name__ == "__main__":
    main()