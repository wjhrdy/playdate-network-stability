# Stable connection lifecycle patterns

## One coordinator

Send every network operation through one authority. Let callers describe origin,
priority, scope, expected duration, retry safety, cancellation policy, and whether
the result is optional. Do not let screens, scenes, or libraries create native
connections outside that policy.

Track at minimum:

```text
queued -> access -> allocated -> operation-pending -> transferring
       -> operation-terminal -> close-requested -> connection-closed -> reusable
                                      \-> incomplete -> quarantined
```

Make completion idempotent. Use operation/generation tokens so late timers and
callbacks cannot finish a replacement operation. Defer close/retry actions from
callbacks to the normal update loop when possible.

## Cancellation and replacement

Use one transition path for every operation replacement:

1. Record the newest requested operation and invalidate older delivery tokens.
2. Stop scheduling optional dependent work.
3. Let the active operation reach a safe terminal state, or retire it exactly
   once.
4. If ownership remains uncertain, quarantine the native object with callbacks
   intact.
5. Start the replacement only when the connection budget permits.
6. Resume optional work after the foreground operation reaches an
   application-defined safe point.

Cancellation of a result is not necessarily cancellation of its native
lifecycle. Suppress delivery when safe cancellation is unavailable, but continue
tracking the object until it settles or enters quarantine.

## Workload profiles

Adapt policy without changing ownership rules:

- **Short HTTP operations:** serialize or tightly bound concurrency; coalesce
  duplicates; verify status, length, and terminal callbacks.
- **Downloads:** drain incrementally, enforce size/total deadlines, and resume
  only from confirmed offsets when the server honors ranges.
- **Uploads and non-idempotent requests:** do not retry automatically unless the
  protocol provides an idempotency key or duplicate-safe semantics.
- **Persistent TCP:** add application heartbeat/liveness rules, track partial
  writes, and avoid mistaking quiet-but-valid periods for failure.
- **Request/response TCP:** use `getSentBytesPending()` to distinguish a queued
  write from a missing response.
- **Mixed workloads:** reserve capacity for foreground work and defer optional
  operations according to application-defined readiness or resource headroom.
- **Continuous media:** additionally monitor decoder/input buffers and underruns;
  treat those as workload health signals rather than connection ownership proof.

## HTTP consumption

Keep one drain function and invoke it from both the response callback and a
guarded update/watchdog poll. Limit bytes or iterations per frame. Update
no-progress time only when headers, native progress, or body bytes advance.

On completion, verify status, transport error, and `Content-Length` when present.
For resumable GETs, preserve confirmed bytes and validate the partial-response
status before joining retained and new data.

## Retry, circuit breaking, and quarantine

Separate three outcomes:

- **Reusable:** required terminal callbacks arrived and integrity checks passed.
- **Failed but settled:** the operation failed and terminal ownership is known.
- **Incomplete:** a required terminal signal is missing or callbacks may still
  arrive.

Keep incomplete objects strongly referenced with guarded callbacks. Bound the
quarantine and expose lost capacity. Stop probing an origin when repeated unsafe
lifecycles would consume the remaining connection budget; serve cached data,
queue work, or fail gracefully until a known recovery boundary.

Treat delivered application data followed by a missing close signal as
incomplete for reuse even when the user-visible operation succeeded.

## Shutdown

Set a terminating flag first. Make callbacks immediate no-ops while code remains
resident. If hardware tests show close, callback removal, or release during module
unload can race firmware work, leave final teardown to the runtime. Test shutdown
from permission-wait, connecting, sending, receiving, retry-wait, close-pending,
and quarantined states.

## Failed approaches and why

- **Independent watchdogs:** overlapping recovery paths create double-close and
  retry races.
- **Fresh object after every stall:** converts one missing callback into session
  exhaustion.
- **Timer-based forced release:** elapsed time does not prove firmware stopped
  referencing a callback or buffer.
- **Wi-Fi cycling:** may change radio state without reclaiming SDK objects and
  adds another asynchronous transition.
- **Global keep-alive:** reduces churn only when reuse is healthy; stale sessions
  can occupy the limited budget.
- **Callbacks only:** delayed callbacks can leave readable bytes or a terminal
  error unnoticed.
- **`getStatus()` only:** access-point connectivity and per-session health are
  different layers.
