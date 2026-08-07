# Playdate networking API notes

Use the installed SDK documentation that matches the target build. The links
below point to Playdate SDK 3.1.1 and may differ from newer headers:

- [C networking API](https://sdk.play.date/3.1.1/Inside%20Playdate%20with%20C.html#_networking)
- [Lua networking API](https://sdk.play.date/3.1.1/Inside%20Playdate.html#networking)

## Capacity and Wi-Fi state

- The 3.1.1 C documentation states that the device supports up to four
  simultaneous connections. Budget globally across HTTP and TCP.
- `network.setEnabled(true)` can begin access-point connection early;
  `setEnabled(false)` turns Wi-Fi off early. The documentation does not describe
  it as a session-table or network-stack reset.
- `network.getStatus()` reports access-point availability. It does not establish
  that a particular socket or HTTP parser is healthy.

## Timeout scope

| API | Scope | Does not prove |
| --- | --- | --- |
| `setConnectTimeout` | Waiting to connect to the server | Request completion, close completion, or object reclamation |
| `setReadTimeout` | How long `read()` waits for incoming bytes | Whole-request failure or callback completion |
| Application no-progress deadline | Time since observed progress | That firmware has stopped referencing callbacks |
| Application total deadline | Wall time for a logical operation | That a native object is safe to release |

Lua timeout arguments use seconds; C timeout arguments use milliseconds in SDK
3.1.1. Verify units against the target SDK rather than copying constants between
languages.

## HTTP signals

- `getError()` returns the last transport error (`nil` in Lua or `NET_OK` in C
  when there is none).
- `getProgress()` returns bytes read and the planned total when known. Query it
  after headers have been parsed.
- `getBytesAvailable()` and `read()` permit guarded polling when a response
  callback is delayed.
- The response callback means bytes are available.
- The request-complete callback fires after known-length data is received or a
  request timeout occurs. It is not synonymous with connection closure.
- The connection-closed callback means the server closed the connection. Do not
  assume it acknowledges every local `close()` call.
- `close()` documents that the object may be used for another request, but reuse
  still requires application state to exclude outstanding callback work.
- `retain()` protects an object from wrapper-lifetime collection, primarily when
  crossing Lua/C ownership. `release()` balances a retain; it is not cancellation.

## TCP signals

- `open()` can report failure synchronously or through its callback. Handle both
  paths exactly once.
- `read()` and `write()` can return negative `PDNetErr` values; never collapse
  them into a generic zero-byte result.
- Treat `NET_BUSY`, `NET_READ_BUSY`, and `NET_WRITE_BUSY` as transient unless the
  target SDK documents otherwise. Classify timeouts, disconnects, failed/reset
  connections, permission failures, and protocol errors as terminal for the
  current logical attempt.
- `write()` is asynchronous. A positive return means bytes entered the network
  stack, not that they reached the peer. Use `getSentBytesPending()` on SDK 3.1+
  to detect a stuck outbound request.
- `close()` returning `NET_OK` means the close request was accepted, not that all
  callback activity has necessarily quiesced.

## Version discipline

Compile against symbolic `PDNetErr` names from the installed header. Do not copy
numeric values across SDK versions: SDK 3.1.1 documentation includes newer error
members that can shift the numeric value of `NET_CONNECTION_CLOSED` compared with
older headers.
