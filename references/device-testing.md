# Device testing and evidence

## Reproduction matrix

Exercise these independently before combining them:

| Dimension | Cases |
| --- | --- |
| Source | live, archive/HLS, metadata-only |
| Transition | live-live, live-archive, archive-live, archive-archive |
| Timing | immediately after start, buffering, steady playback, after hours |
| UI work | browse, search, login, artwork, background refresh |
| Network | good Wi-Fi, weak Wi-Fi, AP loss, recovery |
| Hardware | speaker, headphones, USB power/data, lock/unlock |
| Termination | idle, connecting, receiving, closing, quarantined |

Include rapid switches to expose races and long steady runs to expose retention.
Avoid changing several watchdogs and ownership rules in the same build.

## Telemetry

Log monotonic timestamps and a build identifier. Prefer counters over verbose
per-frame logs:

- HTTP/TCP objects created, reused, active, closing, retired, quarantined, and
  pinned;
- open callbacks pending and request-complete/connection-closed callbacks seen;
- close requests, synchronous close errors, late callbacks, retries, and circuit
  openings;
- bytes received, HTTP polling recoveries, progress advances, exact `PDNetErr`,
  pending-send high-water mark, and outbound send stalls;
- compressed/PCM buffer minima, underruns, frame time, Lua KB, and native heap
  headroom;
- Wi-Fi status as context, never as proof of session health.

Rate-limit periodic summaries so logging does not become the performance problem.
Flush diagnostic logs periodically and at ordinary state transitions.

## Interpreting evidence

- Increasing created/pinned counts with flat reuse suggests incomplete terminal
  lifecycles or unsafe reuse criteria.
- Connected Wi-Fi plus zero progress and `NET_OK` suggests a half-open or silent
  native state; retain a bounded application watchdog.
- Pending outbound bytes identify a send-side stall before response parsing.
- Stable audio buffers while metadata stalls suggest auxiliary HTTP rather than
  decoder or audio-callback failure.
- A crash only during close/release/callback removal is evidence to simplify
  teardown, not to shorten its timer.
- Recovery only after app restart suggests process-owned SDK state, but do not
  claim a firmware leak without allocation and lifecycle evidence.

## Installation and log preservation

Build both targets with the same source revision. Verify checksums when copying a
`.pdx` to hardware. Before reinstalling after a crash, preserve `crashlog.txt`,
`errorlog.txt`, and app data logs from Data Disk mode. Record their source build
and device OS version in filenames or adjacent notes.

Use `scripts/analyze_playdate_network_log.py` to summarize text logs. Preserve the
original files; treat the summary as an index, not a substitute for callback
chronology or crash-register analysis.
