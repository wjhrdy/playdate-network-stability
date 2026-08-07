#!/usr/bin/env python3
"""Summarize Playdate network lifecycle events and key=value counters."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


EVENTS: dict[str, re.Pattern[str]] = {
    "crash": re.compile(r"---\s*crash at|hardfault|hard fault", re.I),
    "request_stall": re.compile(
        r"http:.*(?:request stalled|deadline exceeded)|watchdog .*stalled", re.I
    ),
    "connect_stall": re.compile(r"connect(?:ion)? (?:stalled|timeout)", re.I),
    "send_stall": re.compile(r"send stalled|outbound .* stalled", re.I),
    "session_limit": re.compile(r"session limit|quarantine full|cleanup busy", re.I),
    "poisoned": re.compile(r"poison(?:ed|ing)|unsafe native.*lifecycle", re.I),
    "missing_terminal": re.compile(
        r"missing terminal|without callback|incomplete handle|pinned", re.I
    ),
    "close_stall": re.compile(r"close stalled|could not close|finishing network", re.I),
    "wifi_loss": re.compile(r"wifi=(?:disconnected|unavailable)|not connected to ap", re.I),
    "native_error": re.compile(r"PDNetErr|native error|network: .* failed code=", re.I),
    "retry": re.compile(r"\bretry(?:ing)?\b|reconnecting", re.I),
    "circuit_open": re.compile(r"circuit opened|background.*paused", re.I),
}

METRIC = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)=(-?\d+(?:\.\d+)?)(%|ms|s|kb)?\b")
NETWORK_PREFIXES = ("http_", "tcp_", "stream_", "wifi_")
EXTRA_METRICS = {
    "underruns",
    "lua_kb",
    "heap_block_kb",
    "compressed_min",
    "pcm_min",
}


def iter_lines(paths: list[str]) -> Iterable[tuple[str, int, str]]:
    if paths == ["-"]:
        for number, line in enumerate(sys.stdin, 1):
            yield "<stdin>", number, line.rstrip("\n")
        return
    for raw_path in paths:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                yield str(path), number, line.rstrip("\n")


def analyze(paths: list[str], chronology_limit: int) -> dict[str, object]:
    events: Counter[str] = Counter()
    latest: dict[str, float] = {}
    maxima: dict[str, float] = {}
    chronology: list[dict[str, object]] = []
    line_count = 0

    for source, number, line in iter_lines(paths):
        line_count += 1
        matched: list[str] = []
        for name, pattern in EVENTS.items():
            if pattern.search(line):
                events[name] += 1
                matched.append(name)
        if matched:
            chronology.append(
                {"source": source, "line": number, "events": matched, "text": line}
            )
            if len(chronology) > chronology_limit:
                chronology.pop(0)

        for name, raw_value, _unit in METRIC.findall(line):
            if not (name.startswith(NETWORK_PREFIXES) or name in EXTRA_METRICS):
                continue
            value = float(raw_value)
            latest[name] = value
            maxima[name] = max(maxima.get(name, value), value)

    return {
        "files": paths,
        "lines": line_count,
        "events": dict(sorted(events.items())),
        "latest_metrics": dict(sorted(latest.items())),
        "max_metrics": dict(sorted(maxima.items())),
        "recent_events": chronology,
    }


def print_text(summary: dict[str, object]) -> None:
    print(f"Files: {', '.join(summary['files'])}")
    print(f"Lines: {summary['lines']}")
    print("\nEvents:")
    events = summary["events"]
    if events:
        for name, count in events.items():
            print(f"  {name}: {count}")
    else:
        print("  none detected")

    for heading, key in (("Latest metrics", "latest_metrics"), ("Maximum metrics", "max_metrics")):
        print(f"\n{heading}:")
        metrics = summary[key]
        if metrics:
            for name, value in metrics.items():
                rendered = int(value) if value.is_integer() else value
                print(f"  {name}: {rendered}")
        else:
            print("  none detected")

    print("\nRecent matching lines:")
    recent = summary["recent_events"]
    if recent:
        for item in recent:
            labels = ",".join(item["events"])
            print(f"  {item['source']}:{item['line']} [{labels}] {item['text']}")
    else:
        print("  none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Playdate networking events and diagnostic counters."
    )
    parser.add_argument("logs", nargs="+", help="Text log paths, or - for stdin")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--recent", type=int, default=20, metavar="N", help="Keep the last N matching lines"
    )
    args = parser.parse_args()
    if args.recent < 0:
        parser.error("--recent must be non-negative")
    try:
        summary = analyze(args.logs, args.recent)
    except OSError as error:
        parser.error(str(error))
    if args.json:
        json.dump(summary, sys.stdout, indent=2)
        print()
    else:
        print_text(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
