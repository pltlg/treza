"""Milestone 0 / coupling guard: verify every libagent symbol Signet depends on
exists in the installed version. Run with the project venv:

    .venv\\Scripts\\python.exe spike\\check_symbols.py

Exits non-zero (and lists what's missing) if upstream renamed/moved anything.
This is the seed of the CI upstream-coupling test from Milestone 1.
"""
from __future__ import annotations

import importlib
import inspect
import sys

# (module, attribute, kind) — kind is informational only.
CHECKS = [
    ("libagent.ssh", "serve", "callable"),
    ("libagent.ssh", "parse_config", "callable"),
    ("libagent.ssh", "import_public_keys", "callable"),
    ("libagent.ssh.protocol", "Handler", "class"),
    ("libagent.server", "unix_domain_socket_server", "callable"),
    ("libagent.device.trezor", "Trezor", "class"),
    ("libagent.device.interface", "Identity", "class"),
    ("libagent.device.interface", "string_to_identity", "callable"),
    ("libagent.device.ui", "UI", "class"),
    ("libagent.formats", "export_public_key", "callable"),
    ("libagent.formats", "decompress_pubkey", "callable"),
]

# Methods we override or call on these classes.
METHOD_CHECKS = [
    ("libagent.device.ui", "UI", ["button_request", "get_pin", "get_pairing_code"]),
    ("libagent.device.interface", "Identity", ["get_bip32_address"]),
]


def main() -> int:
    missing: list[str] = []
    found: list[str] = []

    for mod_name, attr, kind in CHECKS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{mod_name} (import failed: {exc!r})")
            continue
        if hasattr(mod, attr):
            obj = getattr(mod, attr)
            sig = ""
            try:
                sig = str(inspect.signature(obj))
            except (TypeError, ValueError):
                pass
            found.append(f"{mod_name}.{attr} {sig}".rstrip())
        else:
            missing.append(f"{mod_name}.{attr} [{kind}]")

    for mod_name, cls_name, methods in METHOD_CHECKS:
        try:
            cls = getattr(importlib.import_module(mod_name), cls_name)
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{mod_name}.{cls_name} (unavailable: {exc!r})")
            continue
        for m in methods:
            qualified = f"{mod_name}.{cls_name}.{m}"
            if hasattr(cls, m):
                found.append(qualified)
            else:
                missing.append(qualified)

    print("=== libagent / trezorlib versions ===")
    for pkg in ("libagent", "trezor", "trezor_agent"):
        try:
            ver = importlib.import_module(pkg.replace("trezor_agent", "trezor_agent")).__version__
        except Exception:  # noqa: BLE001
            try:
                from importlib.metadata import version

                ver = version(pkg)
            except Exception:  # noqa: BLE001
                ver = "?"
        print(f"  {pkg}: {ver}")

    print("\n=== FOUND ===")
    for f in found:
        print(f"  OK  {f}")

    if missing:
        print("\n=== MISSING (upstream changed!) ===")
        for m in missing:
            print(f"  XX  {m}")
        print(f"\n{len(missing)} symbol(s) missing.")
        return 1

    print(f"\nAll {len(found)} symbols present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
