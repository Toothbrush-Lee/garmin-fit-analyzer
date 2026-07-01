#!/usr/bin/env python3
"""Analyze Garmin FIT activity files with Garmin's official FIT Python SDK."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from garmin_fit_sdk import Decoder, Stream


SEMICIRCLES = 2**31
KMH_PER_MPS = 3.6


@dataclass(frozen=True)
class ConversionResult:
    fit_path: Path
    out_dir: Path
    summary_path: Path
    report_path: Path
    records_path: Path
    laps_path: Path
    raw_path: Path | None = None


def semicircles_to_degrees(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) * 180.0 / SEMICIRCLES


def clean_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): clean_value(val) for key, val in value.items()}
    return value


def seconds_to_hms(seconds: float | int | None) -> str | None:
    if seconds is None:
        return None
    whole = int(round(float(seconds)))
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def localize(dt: Any, tz: ZoneInfo) -> str | None:
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).isoformat()


def fit_header(path: Path) -> dict[str, Any]:
    data = path.read_bytes()[:14]
    if len(data) < 12:
        return {"is_fit_header": False, "reason": "file shorter than FIT header"}

    header_size = data[0]
    protocol_version = data[1] / 16
    profile_version_raw = struct.unpack_from("<H", data, 2)[0]
    data_size = struct.unpack_from("<I", data, 4)[0]
    data_type = data[8:12].decode("ascii", errors="replace")
    expected_size = header_size + data_size + 2

    return {
        "is_fit_header": data_type == ".FIT",
        "header_size": header_size,
        "protocol_version": protocol_version,
        "profile_version_raw": profile_version_raw,
        "profile_version": profile_version_raw / 100,
        "data_size_bytes": data_size,
        "expected_file_size_bytes": expected_size,
        "actual_file_size_bytes": path.stat().st_size,
        "data_type": data_type,
    }


def decode_fit(path: Path) -> tuple[dict[str, list[dict[str, Any]]], list[Any], bool]:
    integrity_decoder = Decoder(Stream.from_file(str(path)))
    integrity_ok = integrity_decoder.check_integrity()

    decoder = Decoder(Stream.from_file(str(path)))
    messages, errors = decoder.read(
        apply_scale_and_offset=True,
        convert_datetimes_to_dates=True,
        convert_types_to_strings=True,
        enable_crc_check=True,
        expand_sub_fields=True,
        expand_components=True,
        merge_heart_rates=True,
    )
    return messages, errors, integrity_ok


def values(records: list[dict[str, Any]], field: str) -> list[float]:
    output: list[float] = []
    for record in records:
        value = record.get(field)
        if isinstance(value, (int, float)) and not (
            isinstance(value, float) and math.isnan(value)
        ):
            output.append(float(value))
    return output


def describe(values_: list[float]) -> dict[str, float | None]:
    if not values_:
        return {"min": None, "avg": None, "max": None}
    return {
        "min": min(values_),
        "avg": statistics.fmean(values_),
        "max": max(values_),
    }


def message_counts(messages: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        str(name): len(items) if isinstance(items, list) else 1
        for name, items in sorted(messages.items(), key=lambda item: str(item[0]))
    }


def build_record_rows(
    records: list[dict[str, Any]], start_time: datetime | None, tz: ZoneInfo
) -> tuple[list[dict[str, Any]], list[str]]:
    known_fields = {
        "timestamp",
        "position_lat",
        "position_long",
        "distance",
        "enhanced_speed",
        "enhanced_altitude",
        "heart_rate",
        "cadence",
        "fractional_cadence",
        "cycle_length",
        "cycle_length16",
    }
    extra_fields = sorted(
        {field for record in records for field in record.keys() if field not in known_fields},
        key=lambda field: str(field),
    )
    rows: list[dict[str, Any]] = []
    for record in records:
        timestamp = record.get("timestamp")
        elapsed_s = None
        if isinstance(timestamp, datetime) and isinstance(start_time, datetime):
            elapsed_s = (timestamp - start_time).total_seconds()
        speed_mps = record.get("enhanced_speed")
        row = {
            "timestamp_utc": timestamp.isoformat() if isinstance(timestamp, datetime) else None,
            "timestamp_local": localize(timestamp, tz),
            "elapsed_s": elapsed_s,
            "position_lat_deg": semicircles_to_degrees(record.get("position_lat")),
            "position_long_deg": semicircles_to_degrees(record.get("position_long")),
            "distance_m": record.get("distance"),
            "speed_mps": speed_mps,
            "speed_kmh": speed_mps * KMH_PER_MPS if isinstance(speed_mps, (int, float)) else None,
            "altitude_m": record.get("enhanced_altitude"),
            "heart_rate_bpm": record.get("heart_rate"),
            "cadence_rpm": record.get("cadence"),
            "fractional_cadence_rpm": record.get("fractional_cadence"),
            "cycle_length_m": record.get("cycle_length"),
            "cycle_length16_m": record.get("cycle_length16"),
        }
        for field in extra_fields:
            row[f"extra_{field}"] = clean_value(record.get(field))
        rows.append(row)

    fieldnames = [
        "timestamp_utc",
        "timestamp_local",
        "elapsed_s",
        "position_lat_deg",
        "position_long_deg",
        "distance_m",
        "speed_mps",
        "speed_kmh",
        "altitude_m",
        "heart_rate_bpm",
        "cadence_rpm",
        "fractional_cadence_rpm",
        "cycle_length_m",
        "cycle_length16_m",
        *[f"extra_{field}" for field in extra_fields],
    ]
    return rows, fieldnames


def build_lap_rows(laps: list[dict[str, Any]], tz: ZoneInfo) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, lap in enumerate(laps, start=1):
        distance_m = lap.get("total_distance")
        timer_s = lap.get("total_timer_time")
        avg_speed = lap.get("enhanced_avg_speed")
        rows.append(
            {
                "lap": index,
                "start_time_utc": clean_value(lap.get("start_time")),
                "start_time_local": localize(lap.get("start_time"), tz),
                "duration": seconds_to_hms(timer_s),
                "timer_s": timer_s,
                "distance_km": distance_m / 1000 if isinstance(distance_m, (int, float)) else None,
                "avg_speed_kmh": avg_speed * KMH_PER_MPS
                if isinstance(avg_speed, (int, float))
                else None,
                "max_speed_kmh": lap.get("enhanced_max_speed") * KMH_PER_MPS
                if isinstance(lap.get("enhanced_max_speed"), (int, float))
                else None,
                "avg_hr_bpm": lap.get("avg_heart_rate"),
                "max_hr_bpm": lap.get("max_heart_rate"),
                "calories": lap.get("total_calories"),
                "ascent_m": lap.get("total_ascent"),
                "descent_m": lap.get("total_descent"),
            }
        )
    return rows


def build_hr_zone_rows(time_in_zone_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    session_zone = next(
        (
            item
            for item in time_in_zone_messages
            if item.get("reference_mesg") == "session"
        ),
        None,
    )
    if not session_zone:
        return []

    durations = session_zone.get("time_in_hr_zone") or []
    boundaries = session_zone.get("hr_zone_high_boundary") or []
    total = sum(value for value in durations if isinstance(value, (int, float)))

    rows: list[dict[str, Any]] = []
    for index, seconds in enumerate(durations):
        if index == 0 and boundaries:
            label = f"< {boundaries[0]} bpm"
        elif boundaries and index < len(boundaries):
            label = f"{boundaries[index - 1]}-{boundaries[index] - 1} bpm"
        elif boundaries and index == len(boundaries):
            label = f">= {boundaries[-1]} bpm"
        else:
            label = f"zone {index}"

        rows.append(
            {
                "zone_index": index,
                "label": label,
                "seconds": seconds,
                "duration": seconds_to_hms(seconds),
                "percent": (seconds / total * 100) if total else None,
            }
        )
    return rows


def summarize(
    path: Path,
    messages: dict[str, list[dict[str, Any]]],
    errors: list[Any],
    integrity_ok: bool,
    tz: ZoneInfo,
) -> dict[str, Any]:
    file_id = (messages.get("file_id_mesgs") or [{}])[0]
    activity = (messages.get("activity_mesgs") or [{}])[0]
    session = (messages.get("session_mesgs") or [{}])[0]
    sport = (messages.get("sport_mesgs") or [{}])[0]
    records = messages.get("record_mesgs") or []
    laps = messages.get("lap_mesgs") or []

    start_time = session.get("start_time")
    end_time = session.get("timestamp") or activity.get("timestamp")
    timer_s = session.get("total_timer_time") or activity.get("total_timer_time")
    distance_m = session.get("total_distance")
    avg_speed_mps = session.get("enhanced_avg_speed")
    max_speed_mps = session.get("enhanced_max_speed")

    record_timestamps = [
        record["timestamp"]
        for record in records
        if isinstance(record.get("timestamp"), datetime)
    ]
    record_intervals = [
        (b - a).total_seconds()
        for a, b in zip(record_timestamps, record_timestamps[1:])
        if b > a
    ]
    speed_values = values(records, "enhanced_speed")
    hr_values = values(records, "heart_rate")
    altitude_values = values(records, "enhanced_altitude")

    moving_seconds = 0.0
    for prev, current in zip(records, records[1:]):
        prev_ts = prev.get("timestamp")
        current_ts = current.get("timestamp")
        speed = current.get("enhanced_speed")
        if (
            isinstance(prev_ts, datetime)
            and isinstance(current_ts, datetime)
            and isinstance(speed, (int, float))
            and speed > 0.5
        ):
            moving_seconds += max(0.0, (current_ts - prev_ts).total_seconds())

    return {
        "source_file": str(path),
        "fit_header": fit_header(path),
        "sdk_decode": {
            "official_package": "garmin-fit-sdk",
            "crc_integrity_ok": integrity_ok,
            "decode_error_count": len(errors),
            "decode_errors": [str(error) for error in errors],
        },
        "file_id": clean_value(file_id),
        "activity": {
            "device": file_id.get("garmin_product") or file_id.get("product"),
            "manufacturer": file_id.get("manufacturer"),
            "sport": session.get("sport") or sport.get("sport"),
            "sub_sport": session.get("sub_sport") or sport.get("sub_sport"),
            "sport_profile_name": session.get("sport_profile_name") or sport.get("name"),
            "start_time_utc": clean_value(start_time),
            "start_time_local": localize(start_time, tz),
            "end_time_utc": clean_value(end_time),
            "end_time_local": localize(end_time, tz),
            "duration": seconds_to_hms(timer_s),
            "timer_s": timer_s,
            "distance_km": distance_m / 1000 if isinstance(distance_m, (int, float)) else None,
            "avg_speed_kmh": avg_speed_mps * KMH_PER_MPS
            if isinstance(avg_speed_mps, (int, float))
            else None,
            "max_speed_kmh": max_speed_mps * KMH_PER_MPS
            if isinstance(max_speed_mps, (int, float))
            else None,
            "calories": session.get("total_calories"),
            "ascent_m": session.get("total_ascent"),
            "descent_m": session.get("total_descent"),
            "avg_hr_bpm": session.get("avg_heart_rate"),
            "max_hr_bpm": session.get("max_heart_rate"),
            "aerobic_training_effect": session.get("total_training_effect"),
            "anaerobic_training_effect": session.get("total_anaerobic_training_effect"),
            "training_load_peak": session.get("training_load_peak"),
            "start_lat_deg": semicircles_to_degrees(session.get("start_position_lat")),
            "start_lon_deg": semicircles_to_degrees(session.get("start_position_long")),
            "end_lat_deg": semicircles_to_degrees(session.get("end_position_lat")),
            "end_lon_deg": semicircles_to_degrees(session.get("end_position_long")),
        },
        "records": {
            "count": len(records),
            "with_position": sum(
                1
                for record in records
                if "position_lat" in record and "position_long" in record
            ),
            "with_speed": sum(1 for record in records if "enhanced_speed" in record),
            "with_heart_rate": sum(1 for record in records if "heart_rate" in record),
            "recording_interval_seconds": {
                "min": min(record_intervals) if record_intervals else None,
                "median": statistics.median(record_intervals) if record_intervals else None,
                "max": max(record_intervals) if record_intervals else None,
            },
            "estimated_moving_time_speed_gt_0_5_mps": seconds_to_hms(moving_seconds),
            "speed_kmh_from_records": {
                key: value * KMH_PER_MPS if value is not None else None
                for key, value in describe(speed_values).items()
            },
            "heart_rate_bpm_from_records": describe(hr_values),
            "altitude_m_from_records": describe(altitude_values),
            "fields": {
                str(field): count for field, count in Counter(
                    field for record in records for field in record.keys()
                ).most_common()
            },
        },
        "heart_rate_zones": build_hr_zone_rows(messages.get("time_in_zone_mesgs") or []),
        "laps": build_lap_rows(laps, tz),
        "message_counts": message_counts(messages),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: clean_value(row.get(key)) for key in fieldnames})


def format_number(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{suffix}"
    return f"{value}{suffix}"


def markdown_report(summary: dict[str, Any]) -> str:
    activity = summary["activity"]
    records = summary["records"]
    sport_name = activity.get("sport_profile_name")
    sport = activity.get("sport")
    sub_sport = activity.get("sub_sport")
    speed_range = (
        format_number(records["speed_kmh_from_records"].get("min"), 2, " km/h"),
        format_number(records["speed_kmh_from_records"].get("max"), 2, " km/h"),
    )
    altitude_range = (
        format_number(records["altitude_m_from_records"].get("min"), 1, " m"),
        format_number(records["altitude_m_from_records"].get("max"), 1, " m"),
    )
    lines = [
        "# Garmin FIT Analysis",
        "",
        "## Activity Summary",
        "",
        f"- Device: {activity.get('device')}",
        f"- Sport: {sport_name} ({sport}/{sub_sport})",
        f"- Start: {activity.get('start_time_local')} local / {activity.get('start_time_utc')} UTC",
        f"- Duration: {activity.get('duration')}",
        f"- Distance: {format_number(activity.get('distance_km'), 2, ' km')}",
        f"- Avg speed: {format_number(activity.get('avg_speed_kmh'), 2, ' km/h')}",
        f"- Max speed: {format_number(activity.get('max_speed_kmh'), 2, ' km/h')}",
        f"- Calories: {activity.get('calories')}",
        f"- Ascent/descent: {activity.get('ascent_m')} m / {activity.get('descent_m')} m",
        f"- Heart rate: avg {activity.get('avg_hr_bpm')} bpm, max {activity.get('max_hr_bpm')} bpm",
        "- Training effect: aerobic "
        f"{activity.get('aerobic_training_effect')}, anaerobic "
        f"{activity.get('anaerobic_training_effect')}",
        "",
        "## Recording Detail",
        "",
        f"- FIT integrity/CRC: {summary['sdk_decode']['crc_integrity_ok']}",
        f"- Decode errors: {summary['sdk_decode']['decode_error_count']}",
        "- Record rows: "
        f"{records.get('count')} total, {records.get('with_position')} with GPS, "
        f"{records.get('with_heart_rate')} with HR",
        f"- Record interval: median {records['recording_interval_seconds'].get('median')} s",
        "- Estimated moving time (speed > 0.5 m/s): "
        f"{records.get('estimated_moving_time_speed_gt_0_5_mps')}",
        f"- Record speed range: {speed_range[0]} to {speed_range[1]}",
        f"- Record altitude range: {altitude_range[0]} to {altitude_range[1]}",
        "",
        "## Heart Rate Zones",
        "",
        "| Zone | Time | Percent |",
        "| --- | ---: | ---: |",
    ]
    for row in summary["heart_rate_zones"]:
        lines.append(
            f"| {row['label']} | {row['duration']} | {format_number(row['percent'], 1, '%')} |"
        )

    lines.extend(
        [
            "",
            "## Laps",
            "",
            "| Lap | Duration | Distance | Avg speed | Avg HR | Max HR | Calories |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["laps"]:
        lines.append(
            (
                "| {lap} | {duration} | {distance} | {avg_speed} | "
                "{avg_hr} | {max_hr} | {calories} |"
            ).format(
                lap=row["lap"],
                duration=row["duration"],
                distance=format_number(row["distance_km"], 2, " km"),
                avg_speed=format_number(row["avg_speed_kmh"], 2, " km/h"),
                avg_hr=row["avg_hr_bpm"],
                max_hr=row["max_hr_bpm"],
                calories=row["calories"],
            )
        )

    lines.extend(
        [
            "",
            "## Message Counts",
            "",
            "| Message | Count |",
            "| --- | ---: |",
        ]
    )
    for name, count in sorted(
        summary["message_counts"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| {name} | {count} |")

    return "\n".join(lines) + "\n"


def discover_fit_files(inputs: list[Path], recursive: bool = True) -> list[Path]:
    fit_files: list[Path] = []
    for input_path in inputs:
        path = input_path.expanduser().resolve()
        if path.is_file():
            if path.suffix.lower() != ".fit":
                raise ValueError(f"Input file is not a .fit file: {path}")
            fit_files.append(path)
            continue

        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.glob("*")
            fit_files.extend(
                sorted(
                    item.resolve()
                    for item in candidates
                    if item.is_file() and item.suffix.lower() == ".fit"
                )
            )
            continue

        raise FileNotFoundError(f"Input path does not exist: {path}")

    unique_files: list[Path] = []
    seen: set[Path] = set()
    for fit_file in fit_files:
        if fit_file not in seen:
            unique_files.append(fit_file)
            seen.add(fit_file)

    if not unique_files:
        raise FileNotFoundError("No .fit files were found in the provided input paths.")
    return unique_files


def output_dir_for_file(fit_path: Path, base_out_dir: Path, batch_mode: bool) -> Path:
    if not batch_mode:
        return base_out_dir
    return base_out_dir / fit_path.stem


def convert_fit_file(
    fit_path: Path,
    out_dir: Path,
    tz: ZoneInfo,
    raw_json: bool = False,
) -> ConversionResult:
    out_dir.mkdir(parents=True, exist_ok=True)

    messages, errors, integrity_ok = decode_fit(fit_path)
    summary = summarize(fit_path, messages, errors, integrity_ok, tz)

    stem = fit_path.stem
    summary_path = out_dir / f"{stem}_summary.json"
    report_path = out_dir / f"{stem}_report.md"
    records_path = out_dir / f"{stem}_records.csv"
    laps_path = out_dir / f"{stem}_laps.csv"

    summary_path.write_text(
        json.dumps(clean_value(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(markdown_report(summary), encoding="utf-8")

    start_time = (messages.get("session_mesgs") or [{}])[0].get("start_time")
    record_rows, record_fieldnames = build_record_rows(
        messages.get("record_mesgs") or [],
        start_time if isinstance(start_time, datetime) else None,
        tz,
    )
    write_csv(records_path, record_rows, record_fieldnames)
    write_csv(laps_path, summary["laps"])

    raw_path = None
    if raw_json:
        raw_path = out_dir / f"{stem}_decoded_messages.json"
        raw_path.write_text(
            json.dumps(clean_value(messages), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return ConversionResult(
        fit_path=fit_path,
        out_dir=out_dir,
        summary_path=summary_path,
        report_path=report_path,
        records_path=records_path,
        laps_path=laps_path,
        raw_path=raw_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-convert Garmin FIT activity files to JSON, Markdown, and CSV."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="One or more .fit files or directories containing .fit files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output"),
        help="Output directory for converted files",
    )
    parser.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="IANA timezone used for local timestamps",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="When an input is a directory, only convert .fit files directly inside it.",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Also write all decoded FIT messages to JSON. This can include private fields.",
    )
    return parser.parse_args()


def split_interactive_paths(raw_paths: str) -> list[Path]:
    return [
        Path(part.strip().strip('"').strip("'"))
        for part in raw_paths.split("|")
        if part.strip()
    ]


def complete_args_interactively(args: argparse.Namespace) -> argparse.Namespace:
    if args.inputs:
        return args
    if not sys.stdin.isatty():
        raise SystemExit("No input paths provided. Run with --help for usage.")

    print("Garmin FIT Analyzer")
    print("Input can be a .fit file, multiple .fit files, or a folder containing .fit files.")
    raw_inputs = input("FIT file/folder path(s), separate multiple paths with |: ").strip()
    if not raw_inputs:
        raise SystemExit("No input paths provided.")
    args.inputs = split_interactive_paths(raw_inputs)

    raw_out = input(f"Output directory [{args.out}]: ").strip()
    if raw_out:
        args.out = Path(raw_out.strip('"').strip("'"))

    raw_timezone = input(f"Timezone [{args.timezone}]: ").strip()
    if raw_timezone:
        args.timezone = raw_timezone

    raw_recursive = input("Search folders recursively? [Y/n]: ").strip().lower()
    if raw_recursive in {"n", "no"}:
        args.no_recursive = True

    return args


def main() -> None:
    args = complete_args_interactively(parse_args())
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tz = ZoneInfo(args.timezone)
    fit_files = discover_fit_files(args.inputs, recursive=not args.no_recursive)
    batch_mode = len(fit_files) > 1 or any(path.expanduser().resolve().is_dir() for path in args.inputs)

    print(f"Found {len(fit_files)} FIT file(s).")
    failures: list[tuple[Path, Exception]] = []
    for index, fit_path in enumerate(fit_files, start=1):
        file_out_dir = output_dir_for_file(fit_path, out_dir, batch_mode)
        print(f"[{index}/{len(fit_files)}] Converting {fit_path}")
        try:
            result = convert_fit_file(
                fit_path=fit_path,
                out_dir=file_out_dir,
                tz=tz,
                raw_json=args.raw_json,
            )
        except Exception as exc:
            failures.append((fit_path, exc))
            print(f"  Failed: {exc}")
            continue

        print(f"  Wrote {result.summary_path}")
        print(f"  Wrote {result.report_path}")
        print(f"  Wrote {result.records_path}")
        print(f"  Wrote {result.laps_path}")
        if result.raw_path:
            print(f"  Wrote {result.raw_path}")

    converted = len(fit_files) - len(failures)
    print(f"Done. Converted {converted}/{len(fit_files)} file(s). Output: {out_dir}")
    if failures:
        print("Failures:")
        for path, exc in failures:
            print(f"  {path}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
