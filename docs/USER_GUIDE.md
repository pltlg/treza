# Treza user guide

A step-by-step guide to using your Trezor as an SSH key with Treza. For *how the
signing works under the hood*, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md).

> Treza is pre-release. Install from source for now — see the
> [Install on Windows](../README.md#install-on-windows) section (macOS/Linux:
> [Getting started](../README.md#getting-started-from-source-any-os)).

## Before you start

* A **Trezor** (tested on Safe 3) with up-to-date firmware.
* The **OpenSSH client** (`ssh`) — built into Windows 10/11, macOS, and Linux.
* **Windows only:** disable the built-in `ssh-agent` service once, or it will
  fight Treza for the same pipe (admin PowerShell):
  ```powershell
  Stop-Service ssh-agent
  Set-Service ssh-agent -StartupType Disabled
  ```
* **Linux only:** install the Trezor udev rules from
  [`packaging/linux/51-trezor.rules`](../packaging/linux/51-trezor.rules).

## Step 1 — Launch Treza and finish onboarding

1. Plug in and **unlock your Trezor** (enter the PIN on the device).
2. Start the app:
   ```
   python -m treza
   ```
3. On first run a short **wizard** appears: it checks for your device and helps
   you create your first identity. (You can re-do any of this later from the main
   window.)

> **Passphrase users:** the passphrase you enter determines which keys you get.
> Pick one and use it **every time** — a different passphrase (or an empty one)
> produces different SSH keys that your servers won't recognize.

## Step 2 — Add an SSH identity

An identity is one `user@host` — Treza derives a **separate key per identity**.

1. Click **Add…**.
2. Fill in:
   * **User** — your login on the server (e.g. `git` for GitHub, or your username).
   * **Host** — e.g. `github.com` or `server.example.com`.
   * **Port** — leave as *(default)* unless your server uses a non-standard port.
   * **Key type** — **Ed25519** (recommended) or NIST P-256.
3. Click **OK**. The identity appears in the list.

## Step 3 — Start the agent

Click **Start agent**. The status dot turns green and Treza begins serving the
SSH agent (Windows: `\\.\pipe\openssh-ssh-agent`; macOS/Linux: it exports
`SSH_AUTH_SOCK`). You can also start/stop it from the **tray icon**.

## Step 4 — Export your public key and put it on the server

1. Select your identity in the list.
2. Click **Copy public key** (or **Save public key…** for a file).
3. The Trezor asks **"Export SSH public key?"** — confirm on the device.
4. Add the copied line to the server:
   * **A server you control:** append it to `~/.ssh/authorized_keys` on that
     server (one key per line).
   * **GitHub/GitLab:** *Settings → SSH and GPG keys → New SSH key*, paste it.

The exported line looks like:
```
ssh-ed25519 AAAAC3Nz…Zd3i ssh://you@server.example.com
```

## Step 5 — Connect

With the agent running, your normal tools just work — no extra config:

```bash
ssh you@server.example.com
git clone git@github.com:you/repo.git
```

The first time, the Trezor shows **"Sign SSH login for …?"** — confirm on the
device and you're in. **VS Code Remote-SSH** uses the same `ssh`, so it works
automatically too.

Check what the agent is serving anytime:
```bash
ssh-add -l
```

## Daily use

* Leave Treza running in the **tray**; closing the window keeps the agent alive.
* Each login (and `git` push/pull) pops a **confirmation on the device** — a
  quick button press. That prompt is your protection: nothing authenticates
  without it.
* **Stop agent** from the window or tray when you want to disable SSH access.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ssh` doesn't prompt the device / "Permission denied" | Is the agent running (green dot)? Did you add the **right** public key to the server? `ssh-add -l` to confirm the key is offered. |
| Keys changed / server stopped accepting you | You likely unlocked a **different passphrase wallet**. Use the same passphrase you exported the key with. |
| Windows: agent won't start, or `ssh` ignores Treza | The built-in `ssh-agent` service is running — stop/disable it (see *Before you start*). |
| "No Trezor connected" | Re-plug and unlock the device; on Linux, install the udev rules. |
| Prompt was cancelled / timed out | Just retry the action and confirm on the device promptly. |

## Good to know

* The private key **never leaves the device**; Treza stores only your list of
  identity names, not any secret.
* Lost/reset device? Restore the **same seed** (and use the **same passphrase**)
  on a new Trezor and your SSH keys come back unchanged — there is no key file to
  back up.
