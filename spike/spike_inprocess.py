"""Milestone 0 in-process spike.

Proves that a connected Trezor (target: Safe 3) can, *through libagent's Python
API* (not the CLI), derive an SSH public key and sign a challenge for both
supported curves. This is the exact code path Signet's AgentManager will use.

Run with the project venv, device connected & unlocked:

    .venv\\Scripts\\python.exe spike\\spike_inprocess.py --identity ssh://you@example.com
    .venv\\Scripts\\python.exe spike\\spike_inprocess.py --identity ssh://you@example.com --no-sign

Each operation will prompt for physical confirmation ON THE DEVICE.
Exit code 0 = success. Copy the printed public-key lines into a server's
authorized_keys to complete the end-to-end ssh test.
"""
from __future__ import annotations

import argparse
import sys

from libagent import formats
from libagent.device import interface
from libagent.device.trezor import Trezor
from libagent.device.ui import UI


class SpikeUI(UI):
    """UI that announces on-device confirmation prompts to the console."""

    def button_request(self, _code=None):
        print("    >>> CONFIRM ON THE DEVICE NOW (button_request) <<<", flush=True)


def derive_and_sign(device: Trezor, identity_str: str, curve_name: str,
                    do_sign: bool) -> None:
    identity = interface.Identity(identity_str=identity_str, curve_name=curve_name)
    bip32 = identity.get_bip32_address()
    print(f"\n--- {curve_name} ---")
    print(f"  identity   : {identity.to_string()}")
    print(f"  SLIP-13 path: {bip32}")

    vk = device.pubkey(identity)
    pub_line = formats.export_public_key(vk=vk, label=identity_str)
    print(f"  PUBLIC KEY : {pub_line.strip()}")

    # Sanity-check the format.
    parts = pub_line.split()
    expected_type = {
        formats.CURVE_ED25519: "ssh-ed25519",
        formats.CURVE_NIST256: "ecdsa-sha2-nistp256",
    }[curve_name]
    assert parts[0] == expected_type, f"unexpected key type {parts[0]!r}"
    print(f"  format OK  : key type = {parts[0]}")

    if do_sign:
        challenge = b"signet-spike-challenge-0123456789abcdef"
        sig = device.sign(identity, challenge)
        print(f"  signature  : {len(sig)} bytes (hex head: {sig[:8].hex()})")
        assert len(sig) in (64, 65), f"unexpected signature length {len(sig)}"
        print("  SIGNED OK")


def main() -> int:
    parser = argparse.ArgumentParser(description="Signet Milestone 0 spike")
    parser.add_argument("--identity", default="ssh://signet-spike@example.com",
                        help="SSH identity string, e.g. ssh://user@host")
    parser.add_argument("--no-sign", action="store_true",
                        help="only derive public keys, skip signing")
    parser.add_argument("--curve", choices=["ed25519", "nist256p1", "both"],
                        default="both")
    args = parser.parse_args()

    print("Signet Milestone 0 — in-process libagent spike")
    print(f"  identity : {args.identity}")
    print("  Connecting to device (unlock it if prompted)...", flush=True)

    Trezor.ui = SpikeUI(device_type=Trezor)
    device = Trezor()

    curves = (
        [formats.CURVE_ED25519, formats.CURVE_NIST256]
        if args.curve == "both" else [args.curve]
    )

    try:
        # Touch the session first so connection errors are clearly reported.
        _ = device.session
        print("  Device session established.", flush=True)
        for curve in curves:
            derive_and_sign(device, args.identity, curve, do_sign=not args.no_sign)
    except interface.NotFoundError:
        print("\nERROR: no Trezor found. Connect & unlock the device, then retry.")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR: spike failed: {exc!r}")
        import traceback
        traceback.print_exc()
        return 1

    print("\nSPIKE PASSED. Place a printed public-key line in a server's "
          "authorized_keys and test a real ssh login to finish Milestone 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
