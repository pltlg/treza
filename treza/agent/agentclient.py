"""Minimal SSH-agent protocol client.

Talks to a running agent (ours or any OpenSSH-compatible one) over an AF_UNIX
socket (POSIX) or a Windows named pipe. Used by the GUI to read public keys
from the *running* agent — which avoids opening a second, racing device session
while the agent is serving — and by tests to assert the serve loop answers.

Implements just two requests from OpenSSH's PROTOCOL.agent:
``SSH_AGENTC_REQUEST_IDENTITIES`` (11) -> ``SSH_AGENT_IDENTITIES_ANSWER`` (12).
"""
from __future__ import annotations

import base64
import socket
import struct
import sys

SSH_AGENTC_REQUEST_IDENTITIES = 11
SSH_AGENT_IDENTITIES_ANSWER = 12


def _frame(body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + body


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("agent closed connection early")
        buf += chunk
    return buf


def _transact_unix(sock_path: str, body: bytes, timeout: float) -> bytes:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(sock_path)
        s.sendall(_frame(body))  # stream socket: one combined write is fine
        header = _recv_exact(s, 4)
        (length,) = struct.unpack(">I", header)
        return header + _recv_exact(s, length)
    finally:
        s.close()


def _transact_windows(pipe_path: str, body: bytes, timeout: float) -> bytes:
    from libagent.win_server import NamedPipe  # uses pywin32

    pipe = NamedPipe.open(pipe_path)
    pipe.settimeout(timeout)
    try:
        # The server pipe is message-mode and reads the frame as length-then-body
        # (recv(4) then recv(size)), so the prefix and body must be SEPARATE
        # messages. The reply comes back as a single combined message.
        pipe.sendall(struct.pack(">I", len(body)))
        pipe.sendall(body)
        data = pipe.recv(64 * 1024)
        if not data:
            raise ConnectionError("agent returned no data")
        return bytes(data)
    finally:
        try:
            pipe.close()
        except Exception:  # noqa: BLE001 — benign close race after the reply
            pass


def _transact(sock_path: str, body: bytes, timeout: float) -> bytes:
    if sys.platform == "win32":
        return _transact_windows(sock_path, body, timeout)
    return _transact_unix(sock_path, body, timeout)


def _read_ssh_string(buf: bytes, offset: int) -> tuple[bytes, int]:
    (length,) = struct.unpack(">I", buf[offset : offset + 4])
    start = offset + 4
    return buf[start : start + length], start + length


def list_identities(sock_path: str, timeout: float = 30.0) -> list[tuple[bytes, str]]:
    """Return the agent's identities as ``(key_blob, comment)`` pairs."""
    data = _transact(sock_path, bytes([SSH_AGENTC_REQUEST_IDENTITIES]), timeout)
    (length,) = struct.unpack(">I", data[:4])
    body = data[4 : 4 + length]
    if not body or body[0] != SSH_AGENT_IDENTITIES_ANSWER:
        raise AssertionError(f"unexpected agent response type {body[:1]!r}")
    (count,) = struct.unpack(">I", body[1:5])
    offset = 5
    result: list[tuple[bytes, str]] = []
    for _ in range(count):
        blob, offset = _read_ssh_string(body, offset)
        comment, offset = _read_ssh_string(body, offset)
        result.append((blob, comment.decode("utf-8", "replace")))
    return result


def request_identities_count(sock_path: str, timeout: float = 5.0) -> int:
    """Return how many identities the agent lists (convenience for tests)."""
    return len(list_identities(sock_path, timeout))


def authorized_keys_line(key_blob: bytes, comment: str) -> str:
    """Build an OpenSSH ``authorized_keys`` line from an agent key blob."""
    algo, _ = _read_ssh_string(key_blob, 0)
    b64 = base64.b64encode(key_blob).decode("ascii")
    line = f"{algo.decode('ascii')} {b64}"
    return f"{line} {comment}" if comment else line
