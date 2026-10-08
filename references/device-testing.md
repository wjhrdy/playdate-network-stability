# Device testing and evidence

## Reproduction matrix

Exercise dimensions independently before combining them:

| Dimension | Cases |
| --- | --- |
| Transport | Lua HTTP, C HTTP, TCP, mixed Lua/C |
| Operation | short request, upload, download, redirect, persistent connection |
| HTTP framing | content length, chunked, connection-delimited without content length, truncated body |
| Transition | start, cancel, replace, retry, foreground/background handoff |
| Timing | before connect, sending, receiving, quiet/idle, after extended use |
| Network | good Wi-Fi, weak Wi-Fi, AP loss, reconnect |
| System | USB power/data, lock/unlock, sleep/wake, low power |
| Termination | idle, access-wait, connecting, active, closing, quarantined |

Include rapid operation replacement to expose races and long steady runs to
expose retention. Avoid changing several ownership rules and watchdogs in the
same build.

For mixed workloads, combine long playback or another persistent operation,
foreground browsing, a burst of successful downloads, and a partial disconnect.
Test foreground entry while Wi-Fi reports disconnected and a user action whose
authentication token expires before its dependent request. Exercise late
callbacks during retirement so they restart any reuse quiet interval.

On SDK/OS 3.1.2, rerun chunked and missing-`Content-Length` cases to cover the
[HTTP parser fixes](playdate-network-api.md#sdkos-312-http-fixes). A short replay
past a previous crash point verifies that regression only; it does not replace
a soak across background intervals and accumulated failures.

## Telemetry

Log monotonic timestamps and a build identifier. Prefer counters over verbose
per-frame logs:

- HTTP/TCP objects created, reused, active, closing, retired, quarantined, and
  pinned;
- retained-wrapper totals, reuse-wait counts, callback quiet age, and capacity
  rejections (for example, `http_capacity_blocks`);
- operation IDs/generations, origin, purpose, priority, and state transitions;
- access/open callbacks pending and request-complete/connection-closed callbacks
  seen;
- close requests, synchronous errors, late callbacks, retries, circuit openings,
  and optional work rejected by backpressure;
- bytes sent/received, polling recoveries, progress advances, exact `PDNetErr`,
  pending-send high-water mark, and send/no-progress stalls;
- frame time, Lua KB, native heap headroom, and application-defined health
  metrics;
- Wi-Fi status as context, never as proof of session health.

Rate-limit summaries so logging does not become the performance problem. Flush
diagnostic logs periodically and at ordinary state transitions.

## Interpreting evidence

- Increasing created/pinned counts with flat reuse suggests incomplete terminal
  lifecycles or unsafe reuse criteria.
- Successful requests with rising created/reuse-wait counts can exhaust wrapper
  capacity even when active connections and heap readings remain low. Compare
  crash PC/LR and fault registers with allocation chronology across reproductions;
  an allocation-associated fault is evidence, not proof of its underlying cause.
- Connected Wi-Fi plus zero progress and `NET_OK` suggests a half-open or silent
  native state; retain a bounded application watchdog.
- Pending outbound bytes identify a send-side stall before response handling.
- Healthy foreground state while a background operation stalls localizes the
  failure without proving the transport cause.
- A crash only during close/release/callback removal is evidence to simplify
  teardown, not to shorten its timer.
- Recovery only after app restart suggests process-owned SDK state, but does not
  prove a firmware leak without allocation and lifecycle evidence.

## Installation and log preservation

Build Simulator and device targets from the same revision. Verify checksums when
copying a `.pdx` to hardware. Before reinstalling after a crash, preserve
`crashlog.txt`, `errorlog.txt`, and app data logs from Data Disk mode. Record their
source build and device OS version.

Use `scripts/analyze_playdate_network_log.py` to summarize text logs. Add
`--metric-prefix game_` or repeated `--metric NAME` arguments for an app's own
counters. Preserve the original files; treat the summary as an index, not a
substitute for callback chronology or crash-register analysis.
