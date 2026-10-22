# Changelog

## 53.3.0 - 2026-10-22

- Added framework-neutral callback URL parsing and global-address policy enforcement.
- Added DNS-pinned HTTPS transport with fresh A/AAAA resolution, numeric-IP connections, hostname-preserving TLS, disabled redirects, and ignored proxy environment variables.
- Added structured policy and transport errors with stable identifiers and retryability fields.
- Added deterministic resolver, connector, TLS, redirect, proxy, DNS-rebinding, special-address, and secret-leakage tests.
- Added the safe HTTPS consumer contract in `docs/safe-https.md`.
- Added no new dependency; the implementation uses the standard library and the existing `certifi` dependency.