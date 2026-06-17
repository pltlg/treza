"""SSH identity model, public-key export, and persistence.

Thin wrappers over ``libagent`` so Signet stays compatible with the
``trezor-agent`` CLI config format (``<identity|curve>`` per line, read by
``libagent.ssh.parse_config``) and reuses its key derivation / formatting.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import platformdirs
from libagent import formats
from libagent.device import interface
from libagent.ssh import parse_config

# Re-export the two curves libagent supports for SSH.
ED25519 = formats.CURVE_ED25519  # "ed25519"
NIST256 = formats.CURVE_NIST256  # "nist256p1"
SUPPORTED_CURVES: tuple[str, ...] = (ED25519, NIST256)

# SSH key-type token each curve produces, for display/validation.
KEY_TYPE_BY_CURVE = {
    ED25519: "ssh-ed25519",
    NIST256: "ecdsa-sha2-nistp256",
}

_APP = "Signet"


def default_config_path() -> Path:
    """Return the per-user identities config file path for this OS."""
    return Path(platformdirs.user_config_dir(_APP, appauthor=False)) / "identities.conf"


@dataclasses.dataclass(frozen=True)
class SshIdentity:
    """A single SSH identity (one Trezor-derived key per user@host[:port])."""

    user: str
    host: str
    port: int | None = None
    curve: str = ED25519

    def __post_init__(self) -> None:
        if self.curve not in SUPPORTED_CURVES:
            raise ValueError(
                f"unsupported curve {self.curve!r}; expected one of {SUPPORTED_CURVES}"
            )
        if not self.host:
            raise ValueError("host is required")

    @property
    def identity_string(self) -> str:
        """``ssh://user@host[:port]`` — the SLIP-0013 identity string."""
        s = "ssh://"
        if self.user:
            s += f"{self.user}@"
        s += self.host
        if self.port:
            s += f":{self.port}"
        return s

    @property
    def key_type(self) -> str:
        """The OpenSSH key-type token this identity will export as."""
        return KEY_TYPE_BY_CURVE[self.curve]

    def to_libagent(self) -> interface.Identity:
        """Build the ``libagent`` Identity, with ``proto`` forced to ``ssh``.

        Matches what ``libagent.ssh.main`` does before serving, so derived keys
        are identical to the stock CLI.
        """
        ident = interface.Identity(identity_str=self.identity_string, curve_name=self.curve)
        ident.identity_dict["proto"] = "ssh"
        return ident

    def to_config_line(self) -> str:
        """Serialize to libagent's ``<ssh://user@host|curve>`` config form."""
        return self.to_libagent().to_string()

    @classmethod
    def from_libagent(cls, ident: interface.Identity) -> SshIdentity:
        """Build from a parsed ``libagent`` Identity."""
        d = ident.identity_dict
        port = d.get("port")
        return cls(
            user=d.get("user", ""),
            host=d.get("host", ""),
            port=int(port) if port else None,
            curve=ident.curve_name,
        )

    def __str__(self) -> str:
        base = f"{self.user}@{self.host}" if self.user else self.host
        return f"{base}:{self.port}" if self.port else base


def export_public_key(device: interface.Device, identity: SshIdentity,
                      label: str | None = None) -> str:
    """Derive and format the OpenSSH ``authorized_keys`` line for ``identity``.

    ``device`` is any ``libagent.device.interface.Device`` (real ``Trezor`` or
    ``FakeDevice`` in tests). Triggers on-device confirmation for a real Trezor.
    Returns a single line, e.g. ``ssh-ed25519 AAAA... ssh://user@host``.
    """
    li = identity.to_libagent()
    vk = device.pubkey(li)
    return formats.export_public_key(vk=vk, label=label or identity.identity_string).strip()


class IdentityStore:
    """Load/save the user's identity list in libagent-compatible config form."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> list[SshIdentity]:
        """Read identities from disk (empty list if the file does not exist)."""
        if not self.path.exists():
            return []
        contents = self.path.read_text(encoding="utf-8")
        return [SshIdentity.from_libagent(i) for i in parse_config(contents)]

    def save(self, identities: list[SshIdentity]) -> None:
        """Write identities to disk, creating parent dirs as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(i.to_config_line() for i in identities)
        self.path.write_text(body + ("\n" if body else ""), encoding="utf-8")

    def add(self, identity: SshIdentity) -> list[SshIdentity]:
        """Add ``identity`` if not already present; persist and return the list."""
        identities = self.load()
        if identity not in identities:
            identities.append(identity)
            self.save(identities)
        return identities

    def remove(self, identity: SshIdentity) -> list[SshIdentity]:
        """Remove ``identity`` if present; persist and return the list."""
        identities = [i for i in self.load() if i != identity]
        self.save(identities)
        return identities
