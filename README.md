# Signet — Trezor SSH GUI

> **Name is a placeholder.** Check availability before publishing.

A cross-platform desktop app (Windows / macOS / Linux) that lets a **Trezor**
hardware device be used as an SSH key, managed from a GUI — no terminal agent
configuration. Your private key never leaves the device; every signature is
confirmed physically on the Trezor.

Signet is an **integration + GUI layer** on top of
[`romanz/trezor-agent`](https://github.com/romanz/trezor-agent)'s `libagent`
and `trezorlib`. It deliberately does **not** reimplement any cryptography or
the SSH-agent protocol.

## Status

Early development. See [the implementation plan](docs/) and milestones below.

| Milestone | What | State |
|-----------|------|-------|
| M0 | Trezor **Safe 3** spike (real SSH login) | ⏳ hardware pending |
| M1 | Headless agent integration core | ✅ device-independent core done & tested |
| M2 | Key-management UI (PySide6) | ⬜ |
| M3 | System tray + background operation | ⬜ |
| M4 | Onboarding / first-run wizard | ⬜ |
| M5 | Packaging, signing & CI | ⬜ |

### What works today (headless, no GUI yet)

```bash
python -m signet --status                      # detect a connected Trezor
python -m signet --add ssh://user@host          # add an identity (ed25519)
python -m signet --list                         # list stored identities
python -m signet --serve                        # run the SSH agent (Ctrl+C to stop)
```

On Windows the agent serves the OpenSSH-compatible named pipe
`\\.\pipe\openssh-ssh-agent`; on Unix it exports `SSH_AUTH_SOCK`.

## Architecture

* `signet/agent/` — the **only** place that touches `libagent`/`trezorlib`
  (an upstream-coupling seam, guarded by `tests/test_coupling.py`):
  * `manager.py` — `AgentManager`: runs `libagent`'s serve loop in-process on a
    worker thread, with a `stopped → starting → running → waiting_confirmation →
    error` state machine.
  * `ui_bridge.py` — `CallbackUI`: subclasses `libagent.device.ui.UI` to surface
    device confirmation / PIN events as callbacks.
  * `identities.py` — `SshIdentity` + `IdentityStore`: identity model, public-key
    export, and persistence in `libagent`'s `<identity|curve>` config format.
  * `device.py` — connection detection and model/firmware/lock status.

All device I/O happens on one worker thread; `trezorlib` handles are not
thread-safe. GUI consumers must marshal state callbacks onto the UI thread.

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev,gui]"   # Windows; use .venv/bin on Unix
.venv/Scripts/python -m pytest               # unit + fake-device tests (no hardware)
.venv/Scripts/python -m pytest -m hardware -s # acceptance tests (Trezor required)
```

The fake-device tests stand up the **real** `libagent` serve loop backed by
`libagent.device.fake_device.FakeDevice` and talk the SSH-agent protocol to it,
so the agent path is exercised end-to-end without a Trezor.

Pinned dependency set (from the M0 spike): see `spike/requirements.lock.txt`
(`libagent==0.16.1`, `trezor==0.20.1`, `trezor_agent==0.13.0`).

## License

LGPL-3.0-or-later (to be confirmed against `libagent`'s license during M5).
