"""Treza entry point.

With no arguments this launches the graphical app. It also exposes a small
headless CLI over the agent core — useful for development and the Trezor
hardware validation:

    python -m treza                                # launch the GUI
    python -m treza --list                         # show stored identities
    python -m treza --add ssh://user@host          # add an identity (ed25519)
    python -m treza --serve                        # run the agent (Ctrl+C to stop)
    python -m treza --serve --identity ssh://u@h   # serve an ad-hoc identity
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from .agent import device
from .agent.identities import ED25519, NIST256, IdentityStore, SshIdentity


def _parse_identity(s: str, curve: str) -> SshIdentity:
    from libagent.device.interface import string_to_identity

    d = string_to_identity(s)
    port = d.get("port")
    return SshIdentity(
        user=d.get("user", ""),
        host=d.get("host", ""),
        port=int(port) if port else None,
        curve=curve,
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # No arguments → launch the graphical app.
    if not argv:
        from .gui.app import main as gui_main

        return gui_main()

    parser = argparse.ArgumentParser(prog="treza", description=__doc__)
    parser.add_argument("--list", action="store_true", help="list stored identities")
    parser.add_argument("--add", metavar="IDENTITY", help="add ssh://user@host[:port]")
    parser.add_argument("--remove", metavar="IDENTITY", help="remove ssh://user@host[:port]")
    parser.add_argument("--serve", action="store_true", help="run the SSH agent")
    parser.add_argument("--identity", metavar="IDENTITY",
                        help="serve this ad-hoc identity instead of the stored list")
    parser.add_argument("--curve", choices=[ED25519, NIST256], default=ED25519)
    parser.add_argument("--status", action="store_true", help="print device status and exit")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    store = IdentityStore()

    if args.status:
        print(device.read_status().summary)
        return 0

    if args.add:
        ident = _parse_identity(args.add, args.curve)
        store.add(ident)
        print(f"added {ident} ({ident.curve})")
        return 0

    if args.remove:
        ident = _parse_identity(args.remove, args.curve)
        store.remove(ident)
        print(f"removed {ident}")
        return 0

    if args.list:
        identities = store.load()
        if not identities:
            print("(no identities; add one with --add ssh://user@host)")
        for i in identities:
            print(f"{i}  [{i.curve}]")
        return 0

    if args.serve:
        return _serve(store, args)

    parser.print_help()
    print("\n(The graphical interface is not built yet — see Milestone 2.)")
    return 0


def _serve(store: IdentityStore, args: argparse.Namespace) -> int:
    # Imported lazily so --list/--status work even if a device backend import
    # is slow or unavailable.
    from libagent.device.trezor import Trezor

    from .agent.manager import AgentManager, AgentState
    from .agent.ui_bridge import CallbackUI

    if args.identity:
        identities = [_parse_identity(args.identity, args.curve)]
    else:
        identities = store.load()
    if not identities:
        print("no identities to serve; add one with --add ssh://user@host", file=sys.stderr)
        return 1

    def on_state(state: AgentState, err: Exception | None) -> None:
        if state is AgentState.WAITING_CONFIRMATION:
            print(">>> Confirm the operation on your Trezor <<<", flush=True)
        elif state is AgentState.RUNNING:
            print("agent running", flush=True)
        elif state is AgentState.ERROR:
            print(f"agent error: {err!r}", file=sys.stderr, flush=True)

    def on_button(_code: object) -> None:
        print(">>> Confirm the operation on your Trezor <<<", flush=True)

    ui = CallbackUI(Trezor, on_button_request=on_button)
    mgr = AgentManager(Trezor, identities, ui=ui, on_state_change=on_state)
    print(f"serving {len(identities)} identity(ies) on {mgr.sock_path}")
    mgr.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        mgr.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
