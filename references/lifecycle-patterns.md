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

Carry an operation's priority and scope through token refresh, duplicate checks,
and dependent reads or writes. A foreground action can still starve if one of
its prerequisites is classified as optional background work.

## Stable callbacks and reuse

For reusable wrappers, install callback closures once and dispatch through a
strongly referenced holder that tracks the current request. Keep the holder and
closures alive through retirement and shutdown. Replacing callback closures on
each reuse can expose queued firmware work to a closure that Lua may collect;
this was an evidence-supported concern in Nightcap's OS 3.1.1 investigation.

Before assigning a new request, require the relevant terminal callbacks and
response integrity checks. If target-device testing supports an additional quiet
interval, measure it from the most recent callback, including callbacks received
after logical completion. Every late callback restarts that interval. A timer
alone never makes an incomplete lifecycle safe, and a finite quiet interval is
a mitigation rather than proof that no later callback is possible.

Track simultaneous connections separately from all retained native wrappers:
active, completed awaiting reuse, pooled, and quarantined. Bound creation before
the measured unsafe boundary and expose capacity rejection to the caller. Use
bounded waiting or a visible error when no eligible wrapper is available.

In Nightcap build 83 on OS 3.1.1, a 60-second successful-response hold accumulated
wrappers during archive startup; repeated crashes coincided with creation of
the thirteenth wrapper despite stable heap readings. An eight-second quiet
interval and ten-wrapper creation ceiling passed the targeted replay. These are
workload/firmware observations, not SDK capacity guarantees or universal defaults.

## Foreground networking and loading state

Allow an explicit foreground operation to enter the permission/access/request
workflow while Wi-Fi reports disconnected; that workflow can initiate networking.
Handle permission denial and connection failure with bounded deadlines. Waiting
for connected status before submitting any work can leave a loading screen with
no request capable of advancing it.

Give loading states a bounded guard that distinguishes queued, active, and
missing requests. If no request exists after the allowed startup interval, show
a retryable error rather than spinning indefinitely. Do not retry merely because
Wi-Fi status changes while a request is already tracked.

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

Validate the range offset and resource identity as well as the partial-response
status. When recovery requires resolving a fresh URL, preserve the logical
checkpoint (confirmed bytes, segment, or playback position), but discard byte
prefixes unless the refreshed resource is verified to be the same representation.
Bound both segment/request retries and whole-workflow refresh attempts.

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
