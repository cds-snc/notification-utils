"""Security primitives for caller-controlled outbound HTTPS requests."""

from __future__ import annotations

import http.client
import ipaddress
import math
import re
import socket
import ssl
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping, Protocol, TypeAlias
from urllib.parse import urlsplit

import certifi

IPAddress: TypeAlias = ipaddress.IPv4Address | ipaddress.IPv6Address
SocketAddress: TypeAlias = tuple[str, int] | tuple[str, int, int, int]

INVALID_URL = "invalid_url"
UNSUPPORTED_SCHEME = "unsupported_scheme"
USERINFO_NOT_ALLOWED = "userinfo_not_allowed"
FRAGMENT_NOT_ALLOWED = "fragment_not_allowed"
AMBIGUOUS_ENCODING = "ambiguous_encoding"
INVALID_HOST = "invalid_host"
NON_ASCII_HOSTNAME = "non_ascii_hostname"
INVALID_PORT = "invalid_port"
INVALID_RESOLVED_ADDRESS = "invalid_resolved_address"
NO_ADDRESSES = "no_addresses"
UNSAFE_ADDRESS = "unsafe_address"
METADATA_ADDRESS = "metadata_address"
IPV4_MAPPED_IPV6 = "ipv4_mapped_ipv6"
MIXED_DNS_ANSWERS = "mixed_dns_answers"
DNS_RESOLUTION_FAILED = "dns_resolution_failed"
DNS_NO_ADDRESSES = "dns_no_addresses"
CONNECTION_FAILED = "connection_failed"
CONNECTION_TIMEOUT = "connection_timeout"
TLS_CERTIFICATE_FAILED = "tls_certificate_failed"
TLS_FAILED = "tls_failed"
HTTP_IO_FAILED = "http_io_failed"
HTTP_TIMEOUT = "http_timeout"
HTTP_PROTOCOL_FAILED = "http_protocol_failed"
INVALID_METHOD = "invalid_method"
INVALID_HEADER = "invalid_header"
HOST_HEADER_NOT_ALLOWED = "host_header_not_allowed"
INVALID_BODY = "invalid_body"
INVALID_TIMEOUT = "invalid_timeout"
INSECURE_TLS_CONTEXT = "insecure_tls_context"

_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_METADATA_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("100.100.100.200/32"),
    ipaddress.ip_network("168.63.129.16/32"),
    ipaddress.ip_network("169.254.169.254/32"),
    ipaddress.ip_network("169.254.170.2/32"),
    ipaddress.ip_network("fd00:ec2::254/128"),
)
_SPECIAL_USE_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("100::/64"),
    ipaddress.ip_network("2001:1::/48"),
    ipaddress.ip_network("2001:2::/48"),
    ipaddress.ip_network("2001:4:112::/48"),
    ipaddress.ip_network("2001:10::/28"),
    ipaddress.ip_network("2001:20::/28"),
    ipaddress.ip_network("2001:db8::/32"),
    ipaddress.ip_network("3fff::/20"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
)


def _is_valid_port(port: object) -> bool:
    return isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535


class HTTPSSecurityError(Exception):
    """Base class for HTTPS policy and transport failures."""

    def __init__(
        self,
        code: str,
        *,
        category: str,
        retryable: bool,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code
        self.category = category
        self.retryable = retryable
        self.details = MappingProxyType(dict(details or {}))
        super().__init__(code)


class HTTPSPolicyError(HTTPSSecurityError):
    """A permanent HTTPS policy violation."""

    def __init__(self, code: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(code, category="policy", retryable=False, details=details)


class HTTPSTransportError(HTTPSSecurityError):
    """A network, TLS, or HTTP transport failure."""

    def __init__(
        self,
        code: str,
        *,
        retryable: bool = True,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code, category="transport", retryable=retryable, details=details)


@dataclass(frozen=True, slots=True)
class ResolvedAddress:
    """An address returned by an address resolver."""

    family: int
    address: IPAddress
    port: int
    scope_id: int = 0

    @classmethod
    def from_ip(cls, address: str | IPAddress, port: int = 443, scope_id: int = 0) -> ResolvedAddress:
        if isinstance(address, str) and "%" in address:
            raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS)
        try:
            parsed_address = (
                address if isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)) else ipaddress.ip_address(address)
            )
        except ValueError:
            raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS) from None
        if isinstance(parsed_address, ipaddress.IPv6Address) and parsed_address.scope_id:
            raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS)

        if not _is_valid_port(port):
            raise HTTPSPolicyError(INVALID_PORT)
        if not isinstance(scope_id, int) or isinstance(scope_id, bool) or scope_id < 0:
            raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS)

        family = socket.AF_INET6 if isinstance(parsed_address, ipaddress.IPv6Address) else socket.AF_INET
        return cls(family=family, address=parsed_address, port=port, scope_id=scope_id)

    @property
    def sockaddr(self) -> SocketAddress:
        if not _is_valid_port(self.port):
            raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS)
        if self.family == socket.AF_INET:
            return (str(self.address), self.port)
        if self.family == socket.AF_INET6:
            return (str(self.address).split("%", 1)[0], self.port, 0, self.scope_id)
        raise HTTPSPolicyError(INVALID_RESOLVED_ADDRESS)


@dataclass(frozen=True, slots=True)
class HTTPSRequestTarget:
    """A normalized HTTPS request target."""

    hostname: str
    port: int
    path: str
    query: str
    explicit_port: bool = False
    ip_address: IPAddress | None = None

    @property
    def scheme(self) -> str:
        return "https"

    @property
    def is_ip_literal(self) -> bool:
        return self.ip_address is not None

    @property
    def request_target(self) -> str:
        return self.path + (f"?{self.query}" if self.query else "")

    @property
    def host_header(self) -> str:
        host = f"[{self.hostname}]" if isinstance(self.ip_address, ipaddress.IPv6Address) else self.hostname
        return f"{host}:{self.port}" if self.explicit_port else host


class AddressResolver(Protocol):
    """Resolve a hostname to numeric socket addresses."""

    def resolve(self, hostname: str, port: int) -> Iterable[ResolvedAddress]: ...


class AddressConnector(Protocol):
    """Connect to a previously validated numeric address."""

    def connect(self, address: ResolvedAddress, timeout: float) -> socket.socket: ...


def _policy_error(code: str, **details: object) -> HTTPSPolicyError:
    return HTTPSPolicyError(code, details=details)


def _validate_percent_encoding(component: str) -> None:
    index = 0
    while index < len(component):
        if component[index] != "%":
            index += 1
            continue

        if index + 2 >= len(component) or component[index + 1] not in _HEX_DIGITS or component[index + 2] not in _HEX_DIGITS:
            raise _policy_error(AMBIGUOUS_ENCODING)

        decoded_byte = int(component[index + 1 : index + 3], 16)
        if decoded_byte < 0x20 or decoded_byte == 0x7F:
            raise _policy_error(AMBIGUOUS_ENCODING)
        index += 3


def _validate_hostname(hostname: str, netloc: str) -> IPAddress | None:
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        raise _policy_error(NON_ASCII_HOSTNAME) from None

    if not hostname or len(hostname) > 253 or hostname.endswith("."):
        raise _policy_error(INVALID_HOST)

    try:
        ip_address = ipaddress.ip_address(hostname)
    except ValueError:
        ip_address = None

    if ip_address is not None:
        if isinstance(ip_address, ipaddress.IPv6Address) and not netloc.startswith("["):
            raise _policy_error(INVALID_HOST)
        return ip_address

    if ":" in hostname or (hostname.count(".") == 3 and all(part.isdigit() for part in hostname.split("."))):
        raise _policy_error(INVALID_HOST)

    labels = hostname.lower().split(".")
    if any(not _HOST_LABEL.fullmatch(label) for label in labels) or all(label.isdigit() for label in labels):
        raise _policy_error(INVALID_HOST)
    return None


def _parse_port(netloc: str, hostname: str) -> tuple[int, bool]:
    if netloc.startswith("["):
        closing_bracket = netloc.find("]")
        if closing_bracket == -1:
            raise _policy_error(INVALID_HOST)
        suffix = netloc[closing_bracket + 1 :]
        if not suffix:
            return 443, False
        if not suffix.startswith(":"):
            raise _policy_error(INVALID_PORT)
        port_text = suffix[1:]
    else:
        if netloc.count(":") > 1:
            raise _policy_error(INVALID_HOST)
        if ":" not in netloc:
            return 443, False
        port_text = netloc.rsplit(":", 1)[1]

    if not port_text or not port_text.isascii() or not port_text.isdigit():
        raise _policy_error(INVALID_PORT)

    port = int(port_text)
    if not 1 <= port <= 65535:
        raise _policy_error(INVALID_PORT)
    return port, True


def _validate_url_characters(url: str) -> None:
    if any(character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F for character in url):
        raise _policy_error(AMBIGUOUS_ENCODING)
    if "\\" in url:
        raise _policy_error(AMBIGUOUS_ENCODING)


def parse_https_url(url: str) -> HTTPSRequestTarget:
    """Parse and validate an HTTPS URL without performing DNS resolution."""

    if not isinstance(url, str) or not url:
        raise _policy_error(INVALID_URL)
    _validate_url_characters(url)

    try:
        parsed = urlsplit(url)
    except ValueError:
        raise _policy_error(INVALID_URL) from None

    if parsed.scheme.lower() != "https":
        raise _policy_error(UNSUPPORTED_SCHEME)
    if not parsed.netloc:
        raise _policy_error(INVALID_URL)
    if "#" in url:
        raise _policy_error(FRAGMENT_NOT_ALLOWED)
    if "@" in parsed.netloc:
        raise _policy_error(USERINFO_NOT_ALLOWED)
    if "%" in parsed.netloc:
        raise _policy_error(AMBIGUOUS_ENCODING)

    try:
        hostname = parsed.hostname
    except ValueError:
        raise _policy_error(INVALID_HOST) from None
    if hostname is None:
        raise _policy_error(INVALID_HOST)

    port, explicit_port = _parse_port(parsed.netloc, hostname)
    ip_address = _validate_hostname(hostname, parsed.netloc)
    path = parsed.path or "/"
    if not path.startswith("/"):
        raise _policy_error(INVALID_URL)
    try:
        path.encode("ascii")
        parsed.query.encode("ascii")
    except UnicodeEncodeError:
        raise _policy_error(AMBIGUOUS_ENCODING) from None
    _validate_percent_encoding(path)
    _validate_percent_encoding(parsed.query)

    target = HTTPSRequestTarget(
        hostname=hostname.lower(),
        port=port,
        path=path,
        query=parsed.query,
        explicit_port=explicit_port,
        ip_address=ip_address,
    )
    if ip_address is not None:
        validate_address(ResolvedAddress.from_ip(ip_address, port))
    return target


def _address_reason(address: ResolvedAddress) -> str | None:
    if address.family not in (socket.AF_INET, socket.AF_INET6):
        return "unsupported_family"
    if address.family == socket.AF_INET and not isinstance(address.address, ipaddress.IPv4Address):
        return "family_mismatch"
    if address.family == socket.AF_INET6 and not isinstance(address.address, ipaddress.IPv6Address):
        return "family_mismatch"
    if not _is_valid_port(address.port):
        return "invalid_port"
    if isinstance(address.address, ipaddress.IPv6Address):
        if address.address.ipv4_mapped is not None:
            return IPV4_MAPPED_IPV6
        if address.scope_id:
            return "scoped_address"
    if any(address.address in network for network in _METADATA_NETWORKS if address.address.version == network.version):
        return METADATA_ADDRESS
    if any(address.address in network for network in _SPECIAL_USE_NETWORKS if address.address.version == network.version):
        return "special_use"
    if address.address.is_multicast:
        return "multicast"
    if address.address.is_loopback:
        return "loopback"
    if address.address.is_link_local:
        return "link_local"
    if address.address.is_unspecified:
        return "unspecified"
    if address.address.is_reserved:
        return "reserved"
    if address.address.is_private:
        return "private"
    if not address.address.is_global:
        return UNSAFE_ADDRESS
    return None


def validate_address(address: ResolvedAddress) -> ResolvedAddress:
    """Return ``address`` if it is a globally routable, non-special address."""

    if not isinstance(address, ResolvedAddress):
        raise _policy_error(INVALID_RESOLVED_ADDRESS)
    reason = _address_reason(address)
    if reason is None:
        return address
    if reason in {"unsupported_family", "family_mismatch", "invalid_port"}:
        raise _policy_error(INVALID_RESOLVED_ADDRESS, reason=reason)
    if reason == IPV4_MAPPED_IPV6:
        raise _policy_error(IPV4_MAPPED_IPV6, address=str(address.address))
    if reason == METADATA_ADDRESS:
        raise _policy_error(METADATA_ADDRESS, address=str(address.address))
    raise _policy_error(UNSAFE_ADDRESS, address=str(address.address), reason=reason)


def validate_resolved_addresses(addresses: Iterable[ResolvedAddress]) -> tuple[ResolvedAddress, ...]:
    """Validate every resolver answer and return the safe addresses."""

    resolved_addresses = tuple(addresses)
    if not resolved_addresses:
        raise _policy_error(NO_ADDRESSES)

    safe_addresses: list[ResolvedAddress] = []
    unsafe_errors: list[HTTPSPolicyError] = []
    for address in resolved_addresses:
        if not isinstance(address, ResolvedAddress):
            raise _policy_error(INVALID_RESOLVED_ADDRESS)
        try:
            safe_addresses.append(validate_address(address))
        except HTTPSPolicyError as error:
            unsafe_errors.append(error)

    if safe_addresses and unsafe_errors:
        raise _policy_error(
            MIXED_DNS_ANSWERS,
            answer_count=len(resolved_addresses),
            unsafe_answer_count=len(unsafe_errors),
        )
    if unsafe_errors:
        raise unsafe_errors[0]
    return tuple(safe_addresses)


@dataclass(frozen=True, slots=True)
class HTTPSResponse:
    """A fully read HTTPS response."""

    status_code: int
    reason: str
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def status(self) -> int:
        return self.status_code


class SystemAddressResolver:
    """Resolve hostnames with uncached A and AAAA lookups."""

    def resolve(self, hostname: str, port: int) -> tuple[ResolvedAddress, ...]:
        try:
            records = socket.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        except (OSError, ValueError) as error:
            raise HTTPSTransportError(
                DNS_RESOLUTION_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error

        addresses: list[ResolvedAddress] = []
        try:
            for family, _socktype, _protocol, _canonname, sockaddr in records:
                if family == socket.AF_INET:
                    if not isinstance(sockaddr, tuple) or len(sockaddr) < 2:
                        raise ValueError("invalid IPv4 resolver answer")
                    if not isinstance(sockaddr[0], str):
                        raise ValueError("invalid IPv4 resolver address")
                    addresses.append(ResolvedAddress.from_ip(sockaddr[0], int(sockaddr[1])))
                elif family == socket.AF_INET6:
                    if not isinstance(sockaddr, tuple) or len(sockaddr) < 4:
                        raise ValueError("invalid IPv6 resolver answer")
                    if not isinstance(sockaddr[0], str):
                        raise ValueError("invalid IPv6 resolver address")
                    addresses.append(ResolvedAddress.from_ip(sockaddr[0], int(sockaddr[1]), int(sockaddr[3])))
        except (TypeError, ValueError, HTTPSPolicyError) as error:
            raise HTTPSTransportError(
                DNS_RESOLUTION_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error

        if not addresses:
            raise HTTPSTransportError(DNS_NO_ADDRESSES)
        return tuple(addresses)


class SocketAddressConnector:
    """Open a TCP socket to a validated numeric address without proxy handling."""

    def connect(self, address: ResolvedAddress, timeout: float) -> socket.socket:
        validate_address(address)
        connected_socket: socket.socket | None = None
        try:
            connected_socket = socket.socket(address.family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            connected_socket.settimeout(timeout)
            connected_socket.connect(address.sockaddr)
            return connected_socket
        except (socket.timeout, TimeoutError) as error:
            if connected_socket is not None:
                connected_socket.close()
            raise HTTPSTransportError(
                CONNECTION_TIMEOUT,
                details={"exception_type": type(error).__name__},
            ) from error
        except OSError as error:
            if connected_socket is not None:
                connected_socket.close()
            raise HTTPSTransportError(
                CONNECTION_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error


def _default_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=certifi.where())
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _validate_ssl_context(context: object) -> None:
    if isinstance(context, ssl.SSLContext) and (
        context.minimum_version < ssl.TLSVersion.TLSv1_2 or context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname
    ):
        raise _policy_error(INSECURE_TLS_CONTEXT)


def _validate_timeout(timeout: float) -> None:
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise _policy_error(INVALID_TIMEOUT)


def _validate_method(method: str) -> str:
    if not isinstance(method, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", method):
        raise _policy_error(INVALID_METHOD)
    return method.upper()


def _validate_headers(headers: Mapping[str, str] | None, host_header: str) -> dict[str, str]:
    header_items: tuple[tuple[str, str], ...]
    if headers is None:
        header_items = ()
    else:
        try:
            header_items = tuple(headers.items())
        except (AttributeError, TypeError):
            raise _policy_error(INVALID_HEADER) from None

    normalized_headers: dict[str, str] = {}
    lower_names: set[str] = set()
    for name, value in header_items:
        if not isinstance(name, str) or not isinstance(value, str) or not name:
            raise _policy_error(INVALID_HEADER)
        if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
            raise _policy_error(INVALID_HEADER)
        if name.lower() == "host":
            raise _policy_error(HOST_HEADER_NOT_ALLOWED)
        lower_name = name.lower()
        if lower_name in lower_names:
            raise _policy_error(INVALID_HEADER)
        lower_names.add(lower_name)
        normalized_headers[name] = value
    normalized_headers["Host"] = host_header
    return normalized_headers


def _normalize_body(body: bytes | bytearray | memoryview | str | None) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, str):
        return body.encode("utf-8")
    if isinstance(body, (bytes, bytearray, memoryview)):
        return bytes(body)
    raise _policy_error(INVALID_BODY)


def _validate_target(target: HTTPSRequestTarget) -> HTTPSRequestTarget:
    if not isinstance(target, HTTPSRequestTarget):
        raise _policy_error(INVALID_URL)
    if not isinstance(target.hostname, str) or not isinstance(target.path, str) or not isinstance(target.query, str):
        raise _policy_error(INVALID_URL)
    if not isinstance(target.explicit_port, bool) or not isinstance(target.port, int) or isinstance(target.port, bool):
        raise _policy_error(INVALID_URL)
    if not 1 <= target.port <= 65535:
        raise _policy_error(INVALID_PORT)
    _validate_url_characters(target.hostname + target.path + target.query)
    try:
        target.hostname.encode("ascii")
        target.path.encode("ascii")
        target.query.encode("ascii")
    except UnicodeEncodeError:
        raise _policy_error(AMBIGUOUS_ENCODING) from None
    if not target.path.startswith("/") or "?" in target.path or "#" in target.path or "#" in target.query:
        raise _policy_error(INVALID_URL)
    _validate_percent_encoding(target.path)
    _validate_percent_encoding(target.query)
    hostname = _validate_hostname(
        target.hostname,
        f"[{target.hostname}]" if ":" in target.hostname else target.hostname,
    )
    if hostname != target.ip_address:
        raise _policy_error(INVALID_HOST)
    if target.ip_address is not None:
        validate_address(ResolvedAddress.from_ip(target.ip_address, target.port))
    return target


class SafeHTTPSClient:
    """Send one HTTPS request to a DNS-pinned, globally routable target."""

    def __init__(
        self,
        resolver: AddressResolver | None = None,
        connector: AddressConnector | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.resolver = resolver or SystemAddressResolver()
        self.connector = connector or SocketAddressConnector()
        self.ssl_context = ssl_context or _default_ssl_context()
        _validate_ssl_context(self.ssl_context)

    def request(
        self,
        method: str,
        target: str | HTTPSRequestTarget,
        *,
        headers: Mapping[str, str] | None = None,
        body: bytes | bytearray | memoryview | str | None = None,
        timeout: float = 10.0,
    ) -> HTTPSResponse:
        normalized_method = _validate_method(method)
        _validate_timeout(timeout)
        request_target = _validate_target(parse_https_url(target) if isinstance(target, str) else target)
        request_headers = _validate_headers(headers, request_target.host_header)
        request_body = _normalize_body(body)

        addresses = self._resolve(request_target)
        last_connection_error: HTTPSTransportError | None = None
        for address in addresses:
            try:
                raw_socket = self.connector.connect(address, timeout)
            except HTTPSTransportError as error:
                if error.code in {CONNECTION_FAILED, CONNECTION_TIMEOUT}:
                    last_connection_error = error
                    continue
                raise
            except (socket.timeout, TimeoutError) as error:
                last_connection_error = HTTPSTransportError(
                    CONNECTION_TIMEOUT,
                    details={"exception_type": type(error).__name__},
                )
                continue
            except OSError as error:
                last_connection_error = HTTPSTransportError(
                    CONNECTION_FAILED,
                    details={"exception_type": type(error).__name__},
                )
                continue

            return self._request_over_socket(
                raw_socket,
                request_target,
                normalized_method,
                request_headers,
                request_body,
                timeout,
            )

        if last_connection_error is not None:
            raise last_connection_error
        raise HTTPSTransportError(CONNECTION_FAILED)

    def _resolve(self, target: HTTPSRequestTarget) -> tuple[ResolvedAddress, ...]:
        if target.ip_address is not None:
            return (validate_address(ResolvedAddress.from_ip(target.ip_address, target.port)),)

        try:
            addresses = tuple(self.resolver.resolve(target.hostname, target.port))
        except HTTPSSecurityError:
            raise
        except Exception as error:
            raise HTTPSTransportError(
                DNS_RESOLUTION_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error
        if not addresses:
            raise HTTPSTransportError(DNS_NO_ADDRESSES)
        return validate_resolved_addresses(addresses)

    def _request_over_socket(
        self,
        raw_socket: socket.socket,
        target: HTTPSRequestTarget,
        method: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HTTPSResponse:
        try:
            tls_socket = self.ssl_context.wrap_socket(raw_socket, server_hostname=target.hostname)
        except ssl.CertificateError as error:
            raw_socket.close()
            raise HTTPSTransportError(
                TLS_CERTIFICATE_FAILED,
                retryable=False,
                details={"exception_type": type(error).__name__},
            ) from error
        except (ssl.SSLError, socket.timeout, TimeoutError, OSError) as error:
            raw_socket.close()
            raise HTTPSTransportError(
                TLS_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error

        connection = http.client.HTTPConnection(target.hostname, target.port, timeout=timeout)
        connection.sock = tls_socket
        try:
            connection.request(method, target.request_target, body=body, headers=dict(headers), encode_chunked=False)
            response = connection.getresponse()
            response_body = response.read()
            response_headers: tuple[tuple[str, str], ...] = tuple((name, value) for name, value in response.getheaders())
            return HTTPSResponse(response.status, response.reason, response_headers, response_body)
        except (socket.timeout, TimeoutError) as error:
            raise HTTPSTransportError(
                HTTP_TIMEOUT,
                details={"exception_type": type(error).__name__},
            ) from error
        except http.client.HTTPException as error:
            raise HTTPSTransportError(
                HTTP_PROTOCOL_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error
        except OSError as error:
            raise HTTPSTransportError(
                HTTP_IO_FAILED,
                details={"exception_type": type(error).__name__},
            ) from error
        finally:
            connection.close()


__all__ = [
    "AMBIGUOUS_ENCODING",
    "AddressConnector",
    "AddressResolver",
    "HTTPSPolicyError",
    "HTTPSResponse",
    "HTTPSSecurityError",
    "HTTPSRequestTarget",
    "HTTPSTransportError",
    "CONNECTION_FAILED",
    "CONNECTION_TIMEOUT",
    "DNS_NO_ADDRESSES",
    "DNS_RESOLUTION_FAILED",
    "FRAGMENT_NOT_ALLOWED",
    "HOST_HEADER_NOT_ALLOWED",
    "HTTP_IO_FAILED",
    "HTTP_PROTOCOL_FAILED",
    "HTTP_TIMEOUT",
    "INVALID_BODY",
    "INVALID_HOST",
    "INVALID_HEADER",
    "INSECURE_TLS_CONTEXT",
    "INVALID_METHOD",
    "INVALID_PORT",
    "INVALID_RESOLVED_ADDRESS",
    "INVALID_TIMEOUT",
    "INVALID_URL",
    "IPV4_MAPPED_IPV6",
    "METADATA_ADDRESS",
    "MIXED_DNS_ANSWERS",
    "NO_ADDRESSES",
    "NON_ASCII_HOSTNAME",
    "ResolvedAddress",
    "SafeHTTPSClient",
    "SocketAddressConnector",
    "SystemAddressResolver",
    "TLS_CERTIFICATE_FAILED",
    "TLS_FAILED",
    "UNSAFE_ADDRESS",
    "UNSUPPORTED_SCHEME",
    "USERINFO_NOT_ALLOWED",
    "parse_https_url",
    "validate_address",
    "validate_resolved_addresses",
]
