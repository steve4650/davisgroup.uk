#!/usr/bin/env python3
"""Generate an iCalendar file from liturgical CSV data."""

from __future__ import annotations

import csv
import datetime
import hashlib
import pathlib
import sys
from collections.abc import Iterable

CSV_FILENAME = "liturgy.csv"
OUTPUT_FILENAME = "../static/liturgy.ics"
QUALIFIER_FIELDS = ["Solemnity", "Holyday of Obligation", "Feast"]


def escape_ical_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def fold_ical_line(line: str, width: int = 75) -> Iterable[str]:
    if len(line) <= width:
        yield line
        return

    yield line[:width]
    remainder = line[width:]
    while remainder:
        yield f" {remainder[: width - 1]}"
        remainder = remainder[width - 1 :]


def normalize_qualifier(value: str) -> str:
    return value.strip()


def get_event_summary(description: str, qualifiers: list[str]) -> str:
    if qualifiers:
        return f"{description} ({', '.join(qualifiers)})"
    return description


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y", "t"}


def build_uid(date: datetime.date, summary: str) -> str:
    digest = hashlib.sha1(f"{date.isoformat()}|{summary}".encode()).hexdigest()
    return f"{digest}@davisgroup.uk"


def read_events(csv_path: pathlib.Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = []
        for row in reader:
            if not row.get("Date") or not row.get("Description"):
                continue
            rows.append(row)
    return rows


def build_ical(events: list[dict[str, str]], now: datetime.datetime) -> str:
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//davisgroup.uk//Liturgy Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    dtstamp = now.strftime("%Y%m%dT%H%M%SZ")

    for row in events:
        try:
            event_date = datetime.date.fromisoformat(row["Date"].strip())
        except ValueError as exc:
            raise ValueError(f"Invalid date in CSV: {row['Date']!r}") from exc

        description = row["Description"].strip()
        qualifiers = [field for field in QUALIFIER_FIELDS if row.get(field) and parse_bool(row[field])]
        summary = get_event_summary(description, qualifiers)

        dtstart = event_date.strftime("%Y%m%d")
        dtend = (event_date + datetime.timedelta(days=1)).strftime("%Y%m%d")
        uid = build_uid(event_date, summary)

        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTAMP:{dtstamp}",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:{escape_ical_text(summary)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    folded_lines: list[str] = []
    for line in lines:
        folded_lines.extend(fold_ical_line(line))

    return "\r\n".join(folded_lines) + "\r\n"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    script_dir = pathlib.Path(__file__).resolve().parent
    csv_path = script_dir / CSV_FILENAME
    output_path = script_dir / OUTPUT_FILENAME

    if len(argv) > 1:
        output_path = pathlib.Path(argv[1])

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    events = read_events(csv_path)
    calendar_text = build_ical(events, datetime.datetime.utcnow())

    output_path.write_text(calendar_text, encoding="utf-8")
    print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
