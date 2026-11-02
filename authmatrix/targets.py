"""Validated immutable origins; hostname transport never consults DNS."""
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import SplitResult, urlsplit


PRIVATE = tuple(ipaddress.ip_network(n) for n in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))
HOSTNAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
                      r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\Z")


@dataclass(frozen=True)
class Target:
    origin: SplitResult
    connect_ip: str | None = None


def scoped_address(value, environment):
    ip = ipaddress.ip_address(value)
    if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.scope_id):
        raise ValueError("Mapped and scoped IPv6 targets are unsupported")
    if not ip.is_loopback and not (
            environment == "staging" and any(ip in net for net in PRIVATE)):
        raise ValueError("Target outside local/private staging scope")
    return ip


def parse_target(matrix):
    version, environment, base = (matrix[k] for k in ("version", "environment", "base_url"))
    url = urlsplit(base)
    port = url.port
    if (url.scheme not in ("http", "https") or url.username is not None
            or url.password is not None or url.path not in ("", "/")
            or url.query or url.fragment or port == 0):
        raise ValueError("Invalid target origin")
    if environment == "staging" and url.scheme != "https":
        raise ValueError("Staging requires verified HTTPS")
    if version == 1:
        scoped_address(url.hostname, environment)
        return Target(url)
    if version != 2 or environment != "staging" or url.scheme != "https":
        raise ValueError("Hostname matrices require version 2 and verified staging HTTPS")
    host = url.hostname
    if not isinstance(host, str) or len(host) > 253 or not HOSTNAME.fullmatch(host):
        raise ValueError("Expected a canonical ASCII hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Use matrix version 1 for literal-IP origins")
    authority = host + (f":{port}" if port is not None else "")
    if base not in (f"https://{authority}", f"https://{authority}/"):
        raise ValueError("Expected a canonical HTTPS hostname origin")
    pin = matrix["connect_ip"]
    if not isinstance(pin, str):
        raise ValueError("Expected a literal pinned IP")
    return Target(url, str(scoped_address(pin, environment)))
