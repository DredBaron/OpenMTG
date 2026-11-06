"""TRUSTED_PROXIES: reverse proxies allowed to report the real client address.

Behind your own reverse proxy (Caddy, Traefik, Nginx Proxy Manager, a Cloudflare tunnel, ...)
every request reaches OpenMTG from the proxy's address. List that address (or network) in
TRUSTED_PROXIES and the client address the proxy puts in X-Forwarded-For is used instead, so
per-address login lockout and rate limits apply to the real client. X-Forwarded-For from any
other sender is ignored, because anyone can put anything in that header.

Empty (the default) trusts no one: the address that connected is used, as before.

entrypoint.sh runs this at container start:

    FORWARDED_ALLOW_IPS=$(python trusted_proxies.py /etc/nginx/openmtg/real_ip.conf)

It refuses to start on an invalid value, writes nginx's real-IP include, and prints the list
uvicorn trusts. nginx decides the client address and passes uvicorn exactly that one address
(see nginx.conf); uvicorn trusts nginx plus the same proxies, so the two can never disagree.
"""
import ipaddress
import os
import re
import sys

NGINX_INCLUDE = "/etc/nginx/openmtg/real_ip.conf"
# uvicorn only ever receives requests from the bundled nginx.
NGINX_TO_UVICORN = "127.0.0.1"

_HOW_TO_FIX = (
    "Set TRUSTED_PROXIES to your reverse proxy's IP address or network, e.g. "
    "TRUSTED_PROXIES=172.30.0.2 or TRUSTED_PROXIES=172.30.0.0/24 (separate several with "
    "commas), or leave it empty if OpenMTG is not behind a reverse proxy."
)


class TrustedProxiesError(ValueError):
    """TRUSTED_PROXIES is not a usable list; the message says why and how to fix it."""


Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse(value: str | None) -> list[Network]:
    """The networks in a TRUSTED_PROXIES value, in order and without duplicates."""
    networks: list[Network] = []
    for entry in (e for e in re.split(r"[,\s]+", value or "") if e):
        if entry == "*":
            raise TrustedProxiesError(
                "TRUSTED_PROXIES must not be '*': that would let any client choose the address "
                "OpenMTG sees. " + _HOW_TO_FIX)
        try:
            network = ipaddress.ip_network(entry, strict=True)
        except ValueError:
            hint = ""
            try:
                hint = f" Did you mean {ipaddress.ip_network(entry, strict=False)}?"
            except ValueError:
                pass
            raise TrustedProxiesError(
                f"TRUSTED_PROXIES entry {entry!r} is not an IP address or network (host names "
                f"are not supported).{hint} " + _HOW_TO_FIX)
        if network.prefixlen == 0:
            raise TrustedProxiesError(
                f"TRUSTED_PROXIES entry {entry!r} covers every address, which would let any "
                "client choose the address OpenMTG sees. " + _HOW_TO_FIX)
        if network not in networks:
            networks.append(network)
    return networks


def _fmt(network: Network) -> str:
    return str(network.network_address) if network.num_addresses == 1 else str(network)


def nginx_config(networks: list[Network]) -> str:
    lines = ["# Written at container start from TRUSTED_PROXIES by entrypoint.sh. Do not edit."]
    if not networks:
        lines.append("# TRUSTED_PROXIES is empty: X-Forwarded-For is ignored and the connecting "
                     "address is used.")
    else:
        lines += [f"set_real_ip_from {_fmt(n)};" for n in networks]
        lines += [
            "real_ip_header X-Forwarded-For;",
            # Walk X-Forwarded-For from the right past every trusted proxy: the first address
            # that is not a trusted proxy is the client. Addresses a client wrote further left
            # are never used.
            "real_ip_recursive on;",
        ]
    return "\n".join(lines) + "\n"


def forwarded_allow_ips(networks: list[Network]) -> str:
    return ",".join([NGINX_TO_UVICORN, *(_fmt(n) for n in networks)])


def main(argv: list[str]) -> int:
    nginx_include = argv[1] if len(argv) > 1 else NGINX_INCLUDE
    try:
        networks = parse(os.environ.get("TRUSTED_PROXIES"))
    except TrustedProxiesError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(nginx_include), exist_ok=True)
    with open(nginx_include, "w") as f:
        f.write(nginx_config(networks))
    if networks:
        print("Trusting X-Forwarded-For from: " + ", ".join(_fmt(n) for n in networks), file=sys.stderr)
    print(forwarded_allow_ips(networks))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
