# Stable connection lifecycle patterns

## One coordinator

Send all network requests through one authority, including playback, archive
segments, redirects, metadata, artwork, authentication, and background refresh.
Let UI code describe priority, scope, retry safety, and whether work is optional;
do not let screens create native connections directly.

Track at minimum:

```text
queued -> access -> allocated -> operation-pending -> receiving
       -> operation-terminal -> close-requested -> connection-closed -> reusable
                                      \-> incomplete -> quarantined
```

Make completion idempotent. Use generation tokens so late timers and callbacks
cannot finish a replacement request. Never initiate a second close/retry from a
callback if the normal update loop can perform it safely.

## Source handoff

Implement one transition path for every source pair:

1. Record only the newest requested destination.
2. Stop or pause optional secondary networking.
3. Retire the active media transport.
4. Wait for its safe terminal state or bounded quarantine decision.
5. Start the destination through the same coordinator.
6. Resume optional work only after playback has sufficient compressed and PCM
   reserve.

When platform limits make concurrent browsing unsafe, make navigation pause or
stop both live and archive playback consistently rather than adding route-specific
exceptions.

## HTTP consumption

Keep one drain function and invoke it from both the response callback and a
guarded update/watchdog poll. Limit bytes or iterations per frame. Update
no-progress time only when headers, native progress, or body bytes advance.

On completion, verify status, transport error, and `Content-Length` when present.
For resumable GETs, preserve confirmed bytes and use a Range request only when the
server's response status makes the retained prefix valid.

## Retry and quarantine

Separate three outcomes:

- **Reusable:** required terminal callbacks arrived and integrity checks passed.
- **Failed but settled:** the operation failed and terminal ownership is known.
- **Poisoned/incomplete:** a required terminal signal is missing or callbacks may
  still arrive.

Keep poisoned objects strongly referenced with guarded callbacks. Bound the
quarantine and expose capacity loss. Do not allocate repeatedly when a background
origin demonstrates an unsafe lifecycle; open a session circuit and serve stale
metadata or disable that origin until restart.

Treat a successful response followed by a missing close signal as incomplete for
reuse even though user-visible data was delivered.

## Shutdown

Set a terminating flag first. Make callbacks immediate no-ops while code remains
resident. If hardware tests show close, callback removal, or release during module
unload can race firmware work, leave final teardown to the runtime. Test shutdown
from connecting, buffering, playing, retry-wait, HTTP-active, HTTP-closing, and
quarantined states.

## Failed approaches and why

- **More watchdogs without one coordinator:** overlapping recovery paths create
  double-close and retry races.
- **Retry with a fresh object after every stall:** converts one missing callback
  into session exhaustion.
- **Timer-based forced release:** elapsed time does not prove firmware stopped
  referencing a callback or buffer.
- **Wi-Fi cycling:** may change radio state without reclaiming SDK connection
  objects and adds another asynchronous state transition.
- **Global keep-alive:** reduces churn only when reuse is healthy; stale persistent
  sessions can instead occupy the limited budget.
- **Relying only on callbacks:** delayed callbacks can leave readable bytes or a
  terminal error unnoticed.
- **Relying only on `getStatus()`:** AP connectivity and per-session health are
  different layers.
