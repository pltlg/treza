"""Minimal SSH-agent protocol client for tests.

Speaks just enough of the agent protocol (RFC draft / OpenSSH PROTOCOL.agent)
to ask a running agent to list its identities, so tests can verify our serve
loop actually answers — without depending on ssh-add's platform-specific
SSH_AUTH_SOCK handling. Connects over an AF_UNIX socket (POSIX) or a Windows
named pipe (reusing libagent's own client helper).
"""
from __future__ import annotations

import socket
import struct
import sys

SSH_AGENTC_REQUEST_IDENTITIES = 11
SSH_AGENT_IDENTITIES_ANSWER = 12


def _frame(body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + body


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


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("agent closed connection early")
        buf += chunk
    return buf


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
        # The server closes its end after replying; FlushFileBuffers on our
        # side then raises a benign "no process on the other end" — ignore it.
        try:
            pipe.close()
        except Exception:  # noqa: BLE001
            pass


def request_identities_count(sock_path: str, timeout: float = 5.0) -> int:
    """Connect to the agent and return the number of identities it lists."""
    body = bytes([SSH_AGENTC_REQUEST_IDENTITIES])
    if sys.platform == "win32":
        data = _transact_windows(sock_path, body, timeout)
    else:
        data = _transact_unix(sock_path, body, timeout)

    (length,) = struct.unpack(">I", data[:4])
    body = data[4 : 4 + length]
    if not body or body[0] != SSH_AGENT_IDENTITIES_ANSWER:
        raise AssertionError(
            f"unexpected agent response type {body[:1]!r} (len={length})"
        )
    (count,) = struct.unpack(">I", body[1:5])
    return count
