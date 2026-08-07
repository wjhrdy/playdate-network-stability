---
name: playdate-network-stability
description: Diagnose, design, and harden Playdate Lua or C networking across HTTP requests, downloads, uploads, leaderboards, cloud saves, persistent TCP, multiplayer, streaming, and mixed workloads. Use when a Playdate app hangs, stalls, exhausts connections, reports Busy despite connected Wi-Fi, fails after cancellation or operation switching, crashes during close/release/shutdown, recovers only after restart, or needs device soak tests and saved-log analysis.
---

# Playdate Network Stability

Build network state machines that remain bounded when the Playdate SDK delays or
omits an expected signal. Treat documented API behavior as authoritative and
field observations as hypotheses until reproduced on the target OS and hardware.

## Start with evidence

1. Record the Playdate OS version, SDK/pdx version, build number, and whether the
   failure occurs on hardware, Simulator, or both.
2. Reproduce the smallest operation sequence, including cancellation,
   replacement, retry, background work, lock/unlock, and termination where
   relevant.
3. Preserve crash logs and timestamped application logs before reinstalling.
4. Run `scripts/analyze_playdate_network_log.py LOG...` for a first-pass event
   inventory and connection-counter summary.
5. Inspect the coordinator, every allocation site, callbacks, retry paths, and
   shutdown code before changing timeouts or adding watchdogs.

Read [references/device-testing.md](references/device-testing.md) when designing
reproduction runs, device telemetry, or crash-log collection.

## Inventory the workload

List every HTTP and TCP producer, its origin, priority, expected duration,
idempotency, cancellation semantics, and maximum concurrency. Include user
actions, periodic tasks, retries, redirects, authentication, and library code.
Identify paths that create native objects outside the shared policy.

Separate logical-operation state from native-object state. One user action may
span permission, connection, redirect, retry, and close lifecycles; a timed-out
user action may still leave a native object awaiting callbacks.

## Apply the lifecycle model

Route network work through one coordinator. Model allocation, operation
acceptance, progress, operation completion, close request, connection closure,
quarantine, and reuse as distinct states. Do not treat a local timeout or
`close()` return as proof that firmware has finished using an object or callback.

Permit reuse only after the required transport terminal events and application
integrity checks arrive. Keep an incomplete object and its callbacks reachable
in a bounded quarantine. Refuse, defer, or degrade lower-priority work when the
quarantine consumes the connection budget.

Read [references/lifecycle-patterns.md](references/lifecycle-patterns.md) before
implementing cleanup, retries, cancellation, operation replacement, background
work, or shutdown.

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

Keep polling guards strict. Never query an object after the state machine has
declared it closed, released, or unavailable.

## Protect scarce connections

Assume a small global budget shared by HTTP and TCP. Serialize when concurrency
is unnecessary, reserve capacity for foreground operations, coalesce duplicates,
and apply application-specific backpressure before starting optional work.
Invalidate abandoned workflows without launching their replacements before the
active lifecycle settles.

Apply retries to logical operations, not blindly to handles. Use exponential
backoff, a retry ceiling, and per-origin circuit breakers. Do not let each retry
allocate another potentially orphaned object. Prefer stale, queued, or unavailable
optional data over exhausting all networking for the process.

## Avoid false fixes

- Do not use `setConnectTimeout()` as cleanup. It only bounds connection
  establishment.
- Do not use `setReadTimeout()` as a whole-operation deadline.
- Do not assume connected `network.getStatus()` means an HTTP/TCP session is
  healthy.
- Do not use `network.setEnabled(false/true)` as a documented network-stack
  reset. It controls Wi-Fi availability and prewarming.
- Do not use `retain()`/`release()` as forced cancellation. They manage wrapper
  lifetime and retain counts.
- Do not clear callbacks or release quarantined objects merely because a grace
  timer expired when late callbacks remain possible.
- Do not enable keep-alive globally without a bounded, origin-specific hardware
  test.
- Do not increase buffers before measuring heap headroom and throughput.

Read [references/playdate-network-api.md](references/playdate-network-api.md)
before relying on API semantics, units, callback meaning, or version-specific
`PDNetErr` values.

## Validate proportionally

Build both Simulator and device targets. Validate at least:

1. Repeated start, cancel, replace, and retry sequences.
2. Sustained use across every periodic/background interval.
3. Foreground work while optional work is queued or active.
4. Wi-Fi loss during permission, connect, send, receive, and close states.
5. Lock, unlock, sleep/wake, and app termination from each lifecycle state.
6. Connection-budget, quarantine, and circuit-breaker exhaustion without a hard
   crash or unbounded allocation.

Compare allocation, reuse, active, closing, pinned/quarantined, terminal
callbacks, retries, exact errors, pending-send high-water marks, frame time, Lua
memory, native heap headroom, and workload-specific health signals. Require a
device soak before calling an ownership change stable.

## Report conclusions precisely

Separate findings into SDK-documented guarantees, hardware/OS observations,
evidence-supported inferences, and mitigations that bound damage without
reclaiming native resources. State when restart is the only verified way to
reclaim an unresolved session. Never claim automatic pruning is safe without a
terminal callback or a hardware stress test proving it.
