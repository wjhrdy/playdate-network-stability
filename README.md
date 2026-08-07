# Playdate Network Stability

An agent skill for diagnosing and hardening HTTP and TCP reliability in
[Playdate](https://play.date/dev/) applications.

It captures practical patterns for applications that stall after extended use,
exhaust the device's limited connections, fail during cancellation or operation
switching, crash during teardown, or recover only after an app restart. It is
designed for general Playdate networking rather than any particular application
or media workload.

## What it covers

- Lua and C HTTP lifecycles
- TCP connection, read, write, and close handling
- Downloads, uploads, leaderboards, cloud saves, multiplayer, and streaming
- Cancellation, replacement, retries, backpressure, and circuit breakers
- Late or missing callbacks and bounded connection quarantine
- Shutdown and callback-lifetime crash prevention
- Device soak testing, telemetry, crash logs, and saved-log analysis

The central rule is simple: route network work through one coordinator and keep
logical operation state separate from native connection ownership. A timeout or
local cancellation can end a user-facing operation without proving that its
underlying SDK object is safe to reuse or release.

## Install

The recommended method is the open-source
[`skills` CLI](https://github.com/vercel-labs/skills), which supports multiple
coding agents:

```sh
npx skills add wjhrdy/playdate-network-stability
```

The installer will prompt for the target agent and installation scope. To make
the skill available globally, use:

```sh
npx skills add wjhrdy/playdate-network-stability --global
```

To inspect the skill before installing it:

```sh
npx skills add wjhrdy/playdate-network-stability --list
```

You can also clone the repository and copy or link it into the skill directory
used by your agent:

```sh
git clone https://github.com/wjhrdy/playdate-network-stability.git
```

## Use

Ask your agent to use the skill while working in a Playdate project. For example:

> Use the playdate-network-stability skill to diagnose why this Playdate app
> stops completing HTTP requests after repeated cancellation and retries.

Useful inputs include:

- the smallest reproducible sequence;
- Playdate OS and SDK versions;
- whether the problem occurs on hardware, Simulator, or both;
- relevant networking, lifecycle, and shutdown code;
- timestamped application logs and Playdate crash logs.

## Included resources

- [`SKILL.md`](SKILL.md) — the core diagnostic and implementation workflow
- [`references/playdate-network-api.md`](references/playdate-network-api.md) —
  HTTP/TCP API semantics, timeout scope, and version cautions
- [`references/lifecycle-patterns.md`](references/lifecycle-patterns.md) —
  coordinator, cancellation, retry, quarantine, and shutdown patterns
- [`references/device-testing.md`](references/device-testing.md) — reproduction
  matrices, telemetry, soak testing, and evidence collection
- [`scripts/analyze_playdate_network_log.py`](scripts/analyze_playdate_network_log.py)
  — a dependency-free first-pass log summarizer

## Analyze a saved log

Run the bundled analyzer with Python 3.9 or newer:

```sh
python3 scripts/analyze_playdate_network_log.py path/to/network.log
```

Emit JSON or collect application-specific counters:

```sh
python3 scripts/analyze_playdate_network_log.py path/to/network.log \
  --json \
  --metric-prefix game_ \
  --metric active_downloads
```

The analyzer indexes likely lifecycle events and `key=value` metrics. Preserve
the original logs: its summary is not a substitute for callback chronology,
source inspection, or crash-register analysis.

## Scope

This skill provides investigation and design guidance, not a replacement
network stack. Playdate SDK behavior can differ by OS, SDK version, Simulator,
and hardware. Treat undocumented recovery behavior as a hypothesis until it has
survived a targeted device test and soak run.

## License

[MIT](LICENSE)
