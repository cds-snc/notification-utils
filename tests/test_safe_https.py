import http.client
import ipaddress
import socket
import ssl
from typing import cast

import notifications_utils.safe_https as safe_https
import pytest
from notifications_utils.safe_https import (
    AMBIGUOUS_ENCODING,
    CONNECTION_FAILED,
    CONNECTION_TIMEOUT,
    DNS_NO_ADDRESSES,
    DNS_RESOLUTION_FAILED,
    FRAGMENT_NOT_ALLOWED,
    HOST_HEADER_NOT_ALLOWED,
    HTTP_IO_FAILED,
    HTTP_PROTOCOL_FAILED,
    HTTP_TIMEOUT,
    INSECURE_TLS_CONTEXT,
    INVALID_HEADER,
    INVALID_HOST,
    INVALID_METHOD,
    INVALID_PORT,
    INVALID_RESOLVED_ADDRESS,
    INVALID_TIMEOUT,
    INVALID_URL,
    IPV4_MAPPED_IPV6,
    METADATA_ADDRESS,
    MIXED_DNS_ANSWERS,
    NON_ASCII_HOSTNAME,
    TLS_CERTIFICATE_FAILED,
    TLS_FAILED,
    UNSAFE_ADDRESS,
    UNSUPPORTED_SCHEME,
    USERINFO_NOT_ALLOWED,
    HTTPSPolicyError,
    HTTPSTransportError,
    ResolvedAddress,
    SafeHTTPSClient,
    SocketCallbackConnector,
    SystemCallbackResolver,
    parse_callback_url,
    validate_address,
    validate_resolved_addresses,
)


class FakeResolver:
    def __init__(self, answer_sets, error=None):
        self.answer_sets = [tuple(answer_set) for answer_set in answer_sets]
        self.error = error
        self.calls = []
        self.call_index = 0

    def resolve(self, hostname, port):
        self.calls.append((hostname, port))
        if self.error is not None:
            raise self.error
        answer_ips = self.answer_sets[min(self.call_index, len(self.answer_sets) - 1)]
        self.call_index += 1
        return tuple(ResolvedAddress.from_ip(answer_ip, port) for answer_ip in answer_ips)


class FakeSocket:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeConnector:
    def __init__(self, error=None):
        self.error = error
        self.calls = []
        self.sockets = []

    def connect(self, address, timeout):
        self.calls.append((address, timeout))
        if self.error is not None:
            raise self.error
        connected_socket = FakeSocket()
        self.sockets.append(connected_socket)
        return connected_socket


class FakeTLSContext:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def wrap_socket(self, raw_socket, server_hostname):
        self.calls.append((raw_socket, server_hostname))
        if self.error is not None:
            raise self.error
        return raw_socket


class FakeHTTPResponse:
    def __init__(self, status=200, reason="OK", headers=(), body=b""):
        self.status = status
        self.reason = reason
        self.headers = tuple(headers)
        self.body = body

    def read(self):
        return self.body

    def getheaders(self):
        return self.headers


class FakeHTTPConnection:
    instances: list["FakeHTTPConnection"] = []
    response = FakeHTTPResponse()
    request_error = None

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.closed = False
        self.requests = []
        self.__class__.instances.append(self)

    def request(self, method, target, body, headers, encode_chunked):
        self.requests.append((method, target, body, headers, encode_chunked))
        if self.__class__.request_error is not None:
            raise self.__class__.request_error

    def getresponse(self):
        return self.__class__.response

    def close(self):
        self.closed = True


@pytest.fixture
def fake_http(monkeypatch):
    FakeHTTPConnection.instances = []
    FakeHTTPConnection.response = FakeHTTPResponse()
    FakeHTTPConnection.request_error = None
    monkeypatch.setattr(safe_https.http.client, "HTTPConnection", FakeHTTPConnection)
    return FakeHTTPConnection


def make_client(answer_sets=(("93.184.216.34",),), connector=None, tls_context=None):
    resolver = FakeResolver(answer_sets)
    connector = connector or FakeConnector()
    tls_context = tls_context or FakeTLSContext()
    client = SafeHTTPSClient(resolver=resolver, connector=connector, ssl_context=cast(ssl.SSLContext, tls_context))
    return client, resolver, connector, tls_context


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("http://example.com/callback", UNSUPPORTED_SCHEME),
        ("ftp://example.com/callback", UNSUPPORTED_SCHEME),
        ("https://user:password@example.com/callback", USERINFO_NOT_ALLOWED),
        ("https://example.com/callback#fragment", FRAGMENT_NOT_ALLOWED),
        ("https://example.com:0/callback", INVALID_PORT),
        ("https://example.com:65536/callback", INVALID_PORT),
        ("https://example.com:unknown/callback", INVALID_PORT),
        ("https://example.com/%", AMBIGUOUS_ENCODING),
        ("https://example.com/%ZZ", AMBIGUOUS_ENCODING),
        ("https://example.com/%0a", AMBIGUOUS_ENCODING),
        ("https://example.com%2eexample/callback", AMBIGUOUS_ENCODING),
        ("https://example.com\\callback", AMBIGUOUS_ENCODING),
        ("https://example.com/call back", AMBIGUOUS_ENCODING),
        ("https://example.com.", INVALID_HOST),
        ("https://example..com", INVALID_HOST),
        ("https://example_com", INVALID_HOST),
        ("https://éxample.com", NON_ASCII_HOSTNAME),
        ("https://[2001:db8::1", INVALID_URL),
    ],
)
def test_parse_callback_url_rejects_unsafe_syntax(url, code):
    with pytest.raises(HTTPSPolicyError) as error:
        parse_callback_url(url)

    assert error.value.code == code
    assert error.value.category == "policy"
    assert error.value.retryable is False


def test_parse_callback_url_normalizes_hostname_and_request_target():
    target = parse_callback_url("https://Example.COM:8443/callback?event=delivered")

    assert target.hostname == "example.com"
    assert target.port == 8443
    assert target.path == "/callback"
    assert target.query == "event=delivered"
    assert target.request_target == "/callback?event=delivered"
    assert target.host_header == "example.com:8443"
    assert target.explicit_port is True


def test_parse_callback_url_normalizes_public_ipv6_literal():
    target = parse_callback_url("https://[2001:4860:4860::8888]/callback")

    assert target.ip_address == ipaddress.ip_address("2001:4860:4860::8888")
    assert target.host_header == "[2001:4860:4860::8888]"


@pytest.mark.parametrize(
    ("address", "code"),
    [
        ("0.0.0.0", UNSAFE_ADDRESS),
        ("10.0.0.1", UNSAFE_ADDRESS),
        ("100.64.0.1", UNSAFE_ADDRESS),
        ("127.0.0.1", UNSAFE_ADDRESS),
        ("169.254.1.1", UNSAFE_ADDRESS),
        ("169.254.169.254", METADATA_ADDRESS),
        ("192.0.2.1", UNSAFE_ADDRESS),
        ("192.0.0.9", UNSAFE_ADDRESS),
        ("192.88.99.1", UNSAFE_ADDRESS),
        ("192.168.1.1", UNSAFE_ADDRESS),
        ("198.18.0.1", UNSAFE_ADDRESS),
        ("198.51.100.1", UNSAFE_ADDRESS),
        ("203.0.113.1", UNSAFE_ADDRESS),
        ("224.0.0.1", UNSAFE_ADDRESS),
        ("255.255.255.255", UNSAFE_ADDRESS),
        ("::", UNSAFE_ADDRESS),
        ("::1", UNSAFE_ADDRESS),
        ("fc00::1", UNSAFE_ADDRESS),
        ("fe80::1", UNSAFE_ADDRESS),
        ("2001:1::1", UNSAFE_ADDRESS),
        ("2001:20::1", UNSAFE_ADDRESS),
        ("2001:db8::1", UNSAFE_ADDRESS),
        ("3fff::1", UNSAFE_ADDRESS),
        ("ff02::1", UNSAFE_ADDRESS),
        ("::ffff:8.8.8.8", IPV4_MAPPED_IPV6),
        ("100.100.100.200", METADATA_ADDRESS),
    ],
)
def test_validate_address_rejects_special_and_non_global_addresses(address, code):
    with pytest.raises(HTTPSPolicyError) as error:
        validate_address(ResolvedAddress.from_ip(address))

    assert error.value.code == code


@pytest.mark.parametrize("address", ["8.8.8.8", "93.184.216.34", "2001:4860:4860::8888"])
def test_validate_address_accepts_global_addresses(address):
    resolved = ResolvedAddress.from_ip(address)

    assert validate_address(resolved) == resolved


def test_validate_address_rejects_malformed_resolver_record():
    malformed = ResolvedAddress(family=socket.AF_INET6, address=ipaddress.ip_address("8.8.8.8"), port=443)

    with pytest.raises(HTTPSPolicyError) as error:
        validate_address(malformed)

    assert error.value.code == INVALID_RESOLVED_ADDRESS


def test_validate_resolved_addresses_rejects_mixed_public_and_private_answers():
    answers = (ResolvedAddress.from_ip("93.184.216.34"), ResolvedAddress.from_ip("10.0.0.1"))

    with pytest.raises(HTTPSPolicyError) as error:
        validate_resolved_addresses(answers)

    assert error.value.code == MIXED_DNS_ANSWERS
    assert error.value.details == {"answer_count": 2, "unsafe_answer_count": 1}


def test_validate_resolved_addresses_rejects_all_unsafe_answers():
    with pytest.raises(HTTPSPolicyError) as error:
        validate_resolved_addresses((ResolvedAddress.from_ip("10.0.0.1"),))

    assert error.value.code == UNSAFE_ADDRESS


def test_system_resolver_requests_uncached_a_and_aaaa_answers(monkeypatch):
    calls = []

    def fake_getaddrinfo(hostname, port, **kwargs):
        calls.append((hostname, port, kwargs))
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
            (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("2001:4860:4860::8888", port, 0, 0)),
        ]

    monkeypatch.setattr(safe_https.socket, "getaddrinfo", fake_getaddrinfo)
    addresses = SystemCallbackResolver().resolve("callback.example", 8443)

    assert [str(address.address) for address in addresses] == ["93.184.216.34", "2001:4860:4860::8888"]
    assert calls == [
        (
            "callback.example",
            8443,
            {"family": socket.AF_UNSPEC, "type": socket.SOCK_STREAM, "proto": socket.IPPROTO_TCP},
        )
    ]


def test_system_resolver_maps_dns_failures_to_transport_error(monkeypatch):
    def failing_getaddrinfo(*args, **kwargs):
        raise socket.gaierror("secret host detail")

    monkeypatch.setattr(safe_https.socket, "getaddrinfo", failing_getaddrinfo)

    with pytest.raises(HTTPSTransportError) as error:
        SystemCallbackResolver().resolve("callback.example", 443)

    assert error.value.code == DNS_RESOLUTION_FAILED
    assert error.value.category == "transport"
    assert error.value.retryable is True
    assert error.value.details == {"exception_type": "gaierror"}
    assert "secret host detail" not in str(error.value)


def test_system_resolver_maps_empty_answers_to_transport_error(monkeypatch):
    monkeypatch.setattr(safe_https.socket, "getaddrinfo", lambda *args, **kwargs: [])

    with pytest.raises(HTTPSTransportError) as error:
        SystemCallbackResolver().resolve("callback.example", 443)

    assert error.value.code == DNS_NO_ADDRESSES
    assert error.value.retryable is True


def test_socket_connector_connects_to_numeric_validated_sockaddr(monkeypatch):
    created = []

    class RecordingSocket:
        def __init__(self, *args):
            self.args = args
            self.timeout = None
            self.connected_to = None
            self.closed = False
            created.append(self)

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect(self, sockaddr):
            self.connected_to = sockaddr

        def close(self):
            self.closed = True

    monkeypatch.setattr(safe_https.socket, "socket", RecordingSocket)
    address = ResolvedAddress.from_ip("93.184.216.34", 8443)

    connected_socket = SocketCallbackConnector().connect(address, 2.5)

    assert connected_socket is created[0]
    assert created[0].args == (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    assert created[0].timeout == 2.5
    assert created[0].connected_to == ("93.184.216.34", 8443)


def test_socket_connector_revalidates_address_before_opening_socket(monkeypatch):
    monkeypatch.setattr(safe_https.socket, "socket", lambda *args: pytest.fail("socket must not open"))

    with pytest.raises(HTTPSPolicyError) as error:
        SocketCallbackConnector().connect(ResolvedAddress.from_ip("10.0.0.1"), 2.5)

    assert error.value.code == UNSAFE_ADDRESS


def test_safe_client_rejects_unverified_ssl_context():
    insecure_context = ssl._create_unverified_context()

    with pytest.raises(HTTPSPolicyError) as error:
        SafeHTTPSClient(ssl_context=insecure_context)

    assert error.value.code == INSECURE_TLS_CONTEXT


def test_safe_client_rejects_mixed_dns_before_connector(fake_http):
    client, resolver, connector, _tls_context = make_client((("93.184.216.34", "10.0.0.1"),))

    with pytest.raises(HTTPSPolicyError) as error:
        client.request("POST", "https://callback.example/hook", body=b"payload")

    assert error.value.code == MIXED_DNS_ANSWERS
    assert resolver.calls == [("callback.example", 443)]
    assert connector.calls == []
    assert fake_http.instances == []


def test_safe_client_resolves_again_and_rejects_rebinding_before_second_connect(fake_http):
    client, resolver, connector, _tls_context = make_client(
        (("93.184.216.34",), ("10.0.0.1",)),
    )

    client.request("POST", "https://callback.example/hook", body=b"first")
    with pytest.raises(HTTPSPolicyError) as error:
        client.request("POST", "https://callback.example/hook", body=b"second")

    assert error.value.code == UNSAFE_ADDRESS
    assert len(resolver.calls) == 2
    assert len(connector.calls) == 1


def test_safe_client_maps_dns_failure_without_leaking_error_text(fake_http):
    resolver = FakeResolver([("93.184.216.34",)], error=RuntimeError("Bearer secret body"))
    connector = FakeConnector()
    client = SafeHTTPSClient(
        resolver=resolver,
        connector=connector,
        ssl_context=cast(ssl.SSLContext, FakeTLSContext()),
    )

    with pytest.raises(HTTPSTransportError) as error:
        client.request("POST", "https://callback.example/hook", body=b"secret body")

    assert error.value.code == DNS_RESOLUTION_FAILED
    assert error.value.details == {"exception_type": "RuntimeError"}
    assert "Bearer" not in str(error.value)
    assert "secret" not in repr(error.value.details)
    assert connector.calls == []


def test_safe_client_connects_to_validated_ip_and_preserves_tls_sni_and_host(fake_http):
    client, resolver, connector, tls_context = make_client()

    response = client.request(
        "post",
        "https://Callback.Example:8443/hook?event=delivered",
        headers={"Authorization": "Bearer secret", "Content-Type": "application/json"},
        body="payload",
        timeout=3.5,
    )

    assert response.status_code == 200
    assert resolver.calls == [("callback.example", 8443)]
    assert str(connector.calls[0][0].address) == "93.184.216.34"
    assert connector.calls[0][0].sockaddr == ("93.184.216.34", 8443)
    assert connector.calls[0][1] == 3.5
    assert tls_context.calls == [(connector.sockets[0], "callback.example")]
    connection = fake_http.instances[0]
    assert connection.host == "callback.example"
    assert connection.port == 8443
    assert connection.timeout == 3.5
    assert connection.sock is connector.sockets[0]
    assert connection.requests == [
        (
            "POST",
            "/hook?event=delivered",
            b"payload",
            {
                "Authorization": "Bearer secret",
                "Content-Type": "application/json",
                "Host": "callback.example:8443",
            },
            False,
        )
    ]


def test_safe_client_returns_redirect_without_following_it(fake_http):
    fake_http.response = FakeHTTPResponse(
        status=307,
        reason="Temporary Redirect",
        headers=(("Location", "https://other.example/hook"),),
    )
    client, _resolver, _connector, _tls_context = make_client()

    response = client.request("POST", "https://callback.example/hook", body=b"payload")

    assert response.status_code == 307
    assert response.headers == (("Location", "https://other.example/hook"),)
    assert len(fake_http.instances) == 1
    assert len(fake_http.instances[0].requests) == 1


def test_safe_client_ignores_proxy_environment(monkeypatch, fake_http):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    client, _resolver, connector, _tls_context = make_client()

    client.request("POST", "https://callback.example/hook", body=b"payload")

    assert len(connector.calls) == 1
    assert str(connector.calls[0][0].address) == "93.184.216.34"


def test_safe_client_rejects_caller_host_header(fake_http):
    client, _resolver, connector, _tls_context = make_client()

    with pytest.raises(HTTPSPolicyError) as error:
        client.request("POST", "https://callback.example/hook", headers={"Host": "10.0.0.1"})

    assert error.value.code == HOST_HEADER_NOT_ALLOWED
    assert connector.calls == []


def test_safe_client_rejects_invalid_method_headers_and_timeout(fake_http):
    client, _resolver, connector, _tls_context = make_client()

    with pytest.raises(HTTPSPolicyError) as method_error:
        client.request("POST\n", "https://callback.example/hook")
    with pytest.raises(HTTPSPolicyError) as header_error:
        client.request("POST", "https://callback.example/hook", headers={"X-Test": "bad\nvalue"})
    with pytest.raises(HTTPSPolicyError) as timeout_error:
        client.request("POST", "https://callback.example/hook", timeout=0)

    assert method_error.value.code == INVALID_METHOD
    assert header_error.value.code == INVALID_HEADER
    assert timeout_error.value.code == INVALID_TIMEOUT
    assert connector.calls == []


@pytest.mark.parametrize(
    ("tls_error", "code", "retryable"),
    [
        (ssl.CertificateError("certificate mismatch"), TLS_CERTIFICATE_FAILED, False),
        (ssl.SSLError("handshake failed"), TLS_FAILED, True),
    ],
)
def test_safe_client_maps_tls_failures(fake_http, tls_error, code, retryable):
    tls_context = FakeTLSContext(error=tls_error)
    client, _resolver, connector, _unused_tls_context = make_client(tls_context=tls_context)

    with pytest.raises(HTTPSTransportError) as error:
        client.request("POST", "https://callback.example/hook", body=b"payload")

    assert error.value.code == code
    assert error.value.retryable is retryable
    assert connector.sockets[0].closed is True


def test_safe_client_maps_connection_timeout_and_does_not_use_http(fake_http):
    connector = FakeConnector(error=socket.timeout("timed out"))
    client, _resolver, _unused_connector, _tls_context = make_client(connector=connector)

    with pytest.raises(HTTPSTransportError) as error:
        client.request("POST", "https://callback.example/hook", body=b"payload")

    assert error.value.code == CONNECTION_TIMEOUT
    assert error.value.retryable is True
    assert fake_http.instances == []


def test_safe_client_maps_connection_failure_after_all_validated_addresses(fake_http):
    connector = FakeConnector(error=OSError("connection refused"))
    client, _resolver, _unused_connector, _tls_context = make_client(
        (("93.184.216.34", "2001:4860:4860::8888"),),
        connector=connector,
    )

    with pytest.raises(HTTPSTransportError) as error:
        client.request("POST", "https://callback.example/hook", body=b"payload")

    assert error.value.code == CONNECTION_FAILED
    assert len(connector.calls) == 2
    assert fake_http.instances == []


@pytest.mark.parametrize(
    ("request_error", "code"),
    [
        (socket.timeout("read timed out"), HTTP_TIMEOUT),
        (http.client.BadStatusLine("invalid status"), HTTP_PROTOCOL_FAILED),
        (OSError("connection reset"), HTTP_IO_FAILED),
    ],
)
def test_safe_client_maps_http_failures_without_secret_leakage(fake_http, request_error, code):
    fake_http.request_error = request_error
    client, _resolver, _connector, _tls_context = make_client()

    with pytest.raises(HTTPSTransportError) as error:
        client.request(
            "POST",
            "https://callback.example/hook?token=secret",
            headers={"Authorization": "Bearer secret"},
            body=b"secret body",
        )

    assert error.value.code == code
    assert "secret" not in str(error.value)
    assert fake_http.instances[0].closed is True
