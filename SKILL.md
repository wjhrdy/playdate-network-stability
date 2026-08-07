---
name: playdate-network-stability
description: Diagnose, design, and harden Playdate Lua or C networking for long-lived audio/video streams, HTTP metadata, rapid source switching, Wi-Fi loss, stalled callbacks, connection/session exhaustion, shutdown crashes, and device-only failures. Use when a Playdate app hangs on network transitions, works again only after restart, reports Busy or connection limits, crashes after close/release, or needs extended-playback tests and saved-log analysis.
---

# Playdate Network Stability

Build network state machines that remain bounded when the Playdate SDK delays or
omits the terminal signal an application expected. Treat documented API behavior
as authoritative and field observations as hypotheses until reproduced on the
target OS and hardware.

## Start with evidence

1. Record the Playdate OS version, SDK/pdx version, build number, and whether the
   failure occurs on hardware, Simulator, or both.
2. Reproduce the smallest transition sequence: live-to-live, live-to-archive,
   archive-to-live, playback-to-browse, lock/unlock, or app termination.
3. Preserve crash logs and timestamped application logs before reinstalling.
4. Run `scripts/analyze_playdate_network_log.py LOG...` for a first-pass event
   inventory and connection-counter summary.
5. Inspect the coordinator, every native allocation site, callbacks, retry paths,
   and shutdown code before changing timeouts or adding watchdogs.

Read [references/device-testing.md](references/device-testing.md) when designing
reproduction runs, device telemetry, or crash-log collection.

## Apply the lifecycle model

Route every HTTP/TCP operation through one coordinator. Model allocation,
operation acceptance, response progress, request completion, close request,
connection closure, quarantine, and reuse as distinct states. Do not treat a
local timeout or `close()` return as proof that firmware has finished using the
object or its callbacks.

Permit reuse only after the terminal events required by that transport and the
application's own integrity checks have arrived. Keep an incomplete object and
its callbacks reachable in a bounded quarantine. Refuse or degrade lower-value
work when the quarantine consumes the connection budget.

Read [references/lifecycle-patterns.md](references/lifecycle-patterns.md) before
implementing cleanup, retry, source switching, background metadata, or shutdown.

## Separate progress detection from cleanup

Use callbacks as the fast path and guarded polling as a fallback:

- For HTTP, poll `getBytesAvailable()`, drain bounded chunks, consult
  `getProgress()` after headers, and poll `getError()` while the handle is known
  open.
- For TCP, inspect negative `read()` results as `PDNetErr`, poll `getError()` when
  no bytes are available, and distinguish transient Busy results from terminal
  transport failures.
- After TCP `write()`, poll `getSentBytesPending()` because acceptance into the
  stack does not prove transmission.
- Maintain separate connect, read, no-progress, and total-operation deadlines.

Keep polling state guards strict. Never query an object after the state machine
has declared it closed, released, or unavailable.

## Protect scarce connections

Assume a small global connection budget. Serialize metadata and artwork, reserve
capacity for user-initiated playback, and gate secondary work on audio buffer
headroom. Coalesce duplicate requests and invalidate abandoned UI workflows
without launching replacement requests before the active lifecycle settles.

Apply retries to logical operations, not blindly to handles. Use exponential
backoff, a retry ceiling, and per-origin circuit breakers. Do not allow each retry
to allocate another potentially orphaned native object. Prefer pausing optional
metadata for the session over losing playback and browsing entirely.

## Avoid false fixes

- Do not use `setConnectTimeout()` as cleanup. It only bounds connection
  establishment.
- Do not use `setReadTimeout()` as a whole-request deadline.
- Do not assume `network.getStatus()` reporting connected means an HTTP/TCP
  session is healthy.
- Do not use `network.setEnabled(false/true)` as a documented network-stack
  reset. It controls Wi-Fi availability and prewarming.
- Do not use `retain()`/`release()` as forced cancellation. They manage wrapper
  lifetime and retain counts.
- Do not clear callbacks or release quarantined objects merely because a grace
  timer expired when device evidence shows late callbacks are possible.
- Do not enable keep-alive globally without a bounded, origin-specific hardware
  test; stale persistent sessions can consume scarce capacity.
- Do not increase buffers before measuring heap headroom and throughput.

Read [references/playdate-network-api.md](references/playdate-network-api.md)
before relying on API semantics, units, callback meaning, or version-specific
`PDNetErr` values.

## Validate proportionally

Build both Simulator and device targets. Validate at least:

1. Repeated source switches faster than normal user input.
2. Live and archive playback long enough to cross metadata refresh cycles.
3. Playback followed by browse/login/metadata operations.
4. Wi-Fi loss during connect, buffering, steady playback, and source handoff.
5. App close, lock, and unlock from each network state.
6. Quarantine and circuit-breaker exhaustion without a hard crash.

Compare connection allocations, reuse, active, closing, pinned/quarantined,
terminal callbacks, retries, errors, pending-send high-water marks, audio
underruns, Lua memory, and largest allocatable native heap block. Require a
device soak before calling a lifecycle change stable.

## Report conclusions precisely

Separate findings into:

- SDK-documented guarantees;
- observations reproduced on specific hardware/OS builds;
- inferences supported by counters or crash addresses;
- mitigations that bound damage without reclaiming native resources.

State explicitly when app restart is the only verified way to reclaim an
unresolved native session. Never claim an automatic prune is safe without a
terminal callback or a hardware stress test proving it.
