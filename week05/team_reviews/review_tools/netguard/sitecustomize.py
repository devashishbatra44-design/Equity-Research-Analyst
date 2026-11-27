"""Network guard for replay review: every outbound socket attempt is logged and refused."""
import os
import socket
import sys

_LOG = os.environ.get("NETGUARD_LOG", "/tmp/netguard.log")


def _record(kind, target):
    import traceback
    frames = [f"{fr.filename.split('/')[-1]}:{fr.lineno}:{fr.name}" for fr in traceback.extract_stack()
              if "equity_research_crewai" in fr.filename or "week02" in fr.filename]
    with open(_LOG, "a", encoding="utf-8") as handle:
        handle.write(f"BLOCKED {kind} {target!r} via {frames[-3:]}\n")


def _blocked_connect(self, address, *args, **kwargs):
    if self.family == getattr(socket, "AF_UNIX", None):
        return _orig_connect(self, address, *args, **kwargs)
    _record("connect", address)
    raise OSError("netguard: network access blocked during replay review")


def _blocked_getaddrinfo(host, *args, **kwargs):
    _record("getaddrinfo", host)
    raise socket.gaierror("netguard: DNS blocked during replay review")


_orig_connect = socket.socket.connect
socket.socket.connect = _blocked_connect
socket.socket.connect_ex = _blocked_connect
socket.getaddrinfo = _blocked_getaddrinfo
