# Safe HTTPS

The safe HTTPS API in `notifications-utils` is framework-neutral and is intended for caller-controlled outbound HTTPS requests, including user-configured callbacks. The released API is available in version `53.3.0`.

## Public API

Import the shared policy and transport directly from `notifications_utils.safe_https`:

```python
from notifications_utils.safe_https import SafeHTTPSClient, parse_callback_url

target = parse_callback_url(callback_url)
response = SafeHTTPSClient().request(
    "POST",
    target,
    headers={"Content-Type": "application/json"},
    body=payload,
    timeout=10.0,
)
```

The main entry points are:

- `parse_callback_url(url) -> HTTPSRequestTarget`: pure HTTPS parsing and target normalization.
- `validate_address(address)` and `validate_resolved_addresses(addresses)`: pure address policy checks.
- `SafeHTTPSClient.request(method, target, headers, body, timeout) -> CallbackResponse`: one safe HTTPS exchange.
- `CallbackResponse`: status code, reason, response headers, and fully read response body.
- `AddressResolver` and `AddressConnector`: injectable resolver and numeric-socket seams for tests.
- `SystemCallbackResolver` and `SocketCallbackConnector`: default production implementations.
- `HTTPSPolicyError` and `HTTPSTransportError`: structured failure types.

The package does not depend on Flask, WTForms, Flask-Babel, request globals, application models, callback payload schemas, retry counts, or callback suspension policy.

## Policy

Callback URLs must use HTTPS and have strict ASCII DNS labels or IPv4/IPv6 literals. The parser rejects unsupported schemes, userinfo, fragments, malformed ports, controls, backslashes, malformed percent encoding, encoded authority text, zone-scoped IPv6, invalid hosts, and non-ASCII hostnames. Unicode/IDNA hostnames are intentionally outside this API.

For hostnames, the transport performs a fresh uncached A/AAAA resolution immediately before each request. Every answer must be globally routable. Private, loopback, link-local, metadata, reserved, multicast, unspecified, documentation, shared, and other non-global addresses are rejected. IPv4-mapped IPv6 answers are rejected. A mixture of safe and unsafe answers is rejected as `mixed_dns_answers`; the safe subset is never selected.

Numeric literals receive the same address policy and do not trigger a second hostname lookup.

## Transport Guarantees

The transport connects directly to the validated numeric address. It does not use proxy environment variables, `requests`, `urllib3`, ordinary hostname connection helpers, or a fallback path that performs a second DNS lookup.

TLS uses certificate verification and hostname checking with the existing `certifi` trust bundle. The normalized callback hostname is retained as:

- `server_hostname` for TLS SNI and certificate validation.
- The HTTP `Host` header.
- The logical hostname passed to the HTTP exchange.

Redirects are disabled. A 3xx response is returned to the caller and never followed. HTTP status handling, callback payload format, retries, and suspension remain consumer responsibilities.

The transport creates a fresh connection for each request and does not log request URLs, headers, bearer tokens, or bodies. Structured errors contain only safe details such as an error code, exception type, address-policy reason, or DNS answer counts.

## Errors

Every `CallbackSecurityError` exposes:

- `code`: stable machine-readable identifier.
- `category`: `policy` or `transport`.
- `retryable`: whether a caller may treat the failure as transient.
- `details`: an immutable mapping of safe structured fields.

`HTTPSPolicyError` failures are permanent and have `retryable == False`. Policy identifiers are:

`invalid_url`, `unsupported_scheme`, `userinfo_not_allowed`, `fragment_not_allowed`, `ambiguous_encoding`, `invalid_host`, `non_ascii_hostname`, `invalid_port`, `invalid_resolved_address`, `no_addresses`, `unsafe_address`, `metadata_address`, `ipv4_mapped_ipv6`, `mixed_dns_answers`, `invalid_method`, `invalid_header`, `host_header_not_allowed`, `invalid_body`, `invalid_timeout`, and `insecure_tls_context`.

`HTTPSTransportError` identifiers are `dns_resolution_failed`, `dns_no_addresses`, `connection_failed`, `connection_timeout`, `tls_certificate_failed`, `tls_failed`, `http_io_failed`, `http_timeout`, and `http_protocol_failed`. DNS, connection, timeout, I/O, and handshake failures are retryable by default. Certificate verification failures are transport failures but are marked non-retryable. A response status code, including a 3xx or 5xx status, is not itself a transport exception.

## Testing Consumers

Tests should inject a resolver implementing `resolve(hostname, port)` and a connector implementing `connect(address, timeout)`. The connector receives a `ResolvedAddress` whose `sockaddr` is the exact numeric endpoint that passed policy. A test TLS context may record `server_hostname`; production contexts must retain certificate verification and hostname checking.

Consumers must use this transport for callbacks. Ordinary HTTP clients and redirect-following requests must not be used for callback delivery, because they can re-resolve hostnames, honor ambient proxies, or follow a redirect to a destination that was never policy-checked.