"""Validation of user-supplied outbound webhook URLs.

Users choose where webhook events are POSTed, so a target must not point at the OpenMTG host
itself or at special-purpose addresses. Private LAN ranges stay allowed because Home Assistant
normally lives there.

The host is resolved once, every address it resolves to is checked, and the request is then sent
to that exact address (with the original Host header and TLS server name), so a DNS answer that
changes between the check and the connection cannot redirect the request.
"""
import ipaddress
import socket
from dataclasses import dataclass, field

import httpx

# Blocked on top of the loopback / link-local / unspecified / multicast / reserved categories.
_EXTRA_BLOCKED_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "0.0.0.0/8",           # "this network": 0.0.0.0 reaches the local host
    "100.100.100.200/32",  # cloud instance metadata service outside link-local
    "fd00:ec2::254/128",   # cloud instance metadata service (IPv6)
))

NOT_ALLOWED_MESSAGE = (
    "Target URL points to an address that is not allowed "
    "(loopback, link-local, multicast or reserved)"
)


class UnsafeTargetError(ValueError):
    """The target URL is malformed, cannot be resolved, or points at a blocked address."""


@dataclass(frozen=True)
class Target:
    url: str                              # request URL with the host replaced by the checked IP
    host_header: str                      # the original host (and port, if given)
    extensions: dict = field(default_factory=dict)  # httpx extensions, e.g. the TLS server name


def _resolve(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(info[4][0] for info in infos))


def is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped or ip.sixtofour
        if embedded is not None and is_blocked(embedded):
            return True
    if (ip.is_loopback or ip.is_link_local or ip.is_unspecified
            or ip.is_multicast or ip.is_reserved):
        return True
    return any(ip.version == net.version and ip in net for net in _EXTRA_BLOCKED_NETWORKS)


def _parse(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
    except Exception:
        raise UnsafeTargetError("Target URL is not a valid URL")
    if parsed.scheme not in ("http", "https"):
        raise UnsafeTargetError("Target URL must start with http:// or https://")
    if parsed.userinfo:
        raise UnsafeTargetError("Target URL must not contain a username or password")
    if not parsed.raw_host:
        raise UnsafeTargetError("Target URL has no host")
    return parsed


def prepare(url: str) -> Target:
    """Check a target URL and pin it to the address it resolves to right now.

    Raises UnsafeTargetError with a message that is safe to show the user."""
    parsed = _parse(url)
    host = parsed.raw_host.decode("ascii")  # IDNA-encoded; IPv6 literals without brackets
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addresses = _resolve(host, port)
    except (OSError, UnicodeError):
        addresses = []
    if not addresses:
        raise UnsafeTargetError("Could not resolve the target URL's host from the OpenMTG server")

    try:
        ips = [ipaddress.ip_address(a.split("%", 1)[0]) for a in addresses]
    except ValueError:
        raise UnsafeTargetError(NOT_ALLOWED_MESSAGE)
    # Every address must pass: the connection could otherwise land on any of them.
    if any(is_blocked(ip) for ip in ips):
        raise UnsafeTargetError(NOT_ALLOWED_MESSAGE)

    is_literal = _is_ip_literal(host)
    host_header = f"[{host}]" if ":" in host else host
    if parsed.port is not None:
        host_header += f":{parsed.port}"
    extensions = {}
    if parsed.scheme == "https" and not is_literal:
        # Certificate checks and SNI use the original name, not the pinned IP.
        extensions["sni_hostname"] = host

    return Target(
        url=str(parsed.copy_with(host=str(ips[0]))),
        host_header=host_header,
        extensions=extensions,
    )


def validate(url: str) -> None:
    """Raise UnsafeTargetError if the URL may not be used as a webhook target."""
    prepare(url)


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
