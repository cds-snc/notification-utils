import argparse
import csv
import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOW_LIST_PATH = REPO_ROOT / "scripts/sms_pricing/allowed_country_list.csv"
DEFAULT_PRICES_PATH = REPO_ROOT / "scripts/sms_pricing/aws_prices_sms_mar_2026.csv"
DEFAULT_PREFIX_FEATURES_PATH = REPO_ROOT / "scripts/sms_pricing/country_prefixes.csv"
DEFAULT_DLR_SNAPSHOT_PATH = REPO_ROOT / "scripts/sms_pricing/dlr_snapshot.yml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "notifications_utils/international_billing_rates.yml"

DEFAULT_BASE_RATE = 0.01507  # NOTE: This is in USD because the rates from AWS are in USD. Rate initially calculated here: https://docs.google.com/document/d/1f4QdbkKuOEF0unomxdGGDTsgzpWTaqDfIJBmSwimsIc/edit?usp=sharing
DEFAULT_DLR = "YES"


@dataclass(frozen=True)
class FeatureCountry:
    country_name: str
    iso_code: str
    prefixes: tuple[str, ...]


ALLOW_NAME_ALIASES = {
    "czech republic": "czechia czech republic",
    "democratic republic of congo": "democratic republic of the congo",
    "macao": "macau",
    "republic of congo": "republic of the congo",
    "south korea": "korea republic of",
    "swaziland": "eswatini",
    "timor leste": "east timor",
}


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower().replace("&", "and")
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return re.sub(r"\s+", " ", ascii_value).strip()


def _parse_prefixes(dialing_code: str) -> tuple[str, ...]:
    prefixes = []
    for raw_prefix in dialing_code.split(","):
        digits = re.sub(r"\D", "", raw_prefix)
        if digits:
            prefixes.append(digits)
    return tuple(sorted(set(prefixes), key=lambda prefix: (len(prefix), prefix)))


def load_allowed_countries(allow_list_path: Path) -> list[str]:
    # Expect a CSV with an ISO column (preferred). Returns a list of ISO
    # codes (uppercased). For backwards compatibility only, a legacy
    # newline-separated list of country names is supported but this script
    # now requires ISO codes for the allow-list.
    if allow_list_path.suffix.lower() == ".csv":
        isos: list[str] = []
        with allow_list_path.open(newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames or []
            iso_col = _get_csv_column_name(
                fieldnames,
                ("ISO_CODE", "ISO code", "ISO", "ISO Code", "ISO Country"),
                "ISO",
            )
            for row in reader:
                iso = (row.get(iso_col) or "").strip().upper()
                if iso:
                    isos.append(iso)
        return isos

    # legacy plain-text allow-list (one country name per line) — convert
    # country names to normalized strings and return them as-is (deprecated)
    countries = []
    seen_normalized = set()
    for line in allow_list_path.read_text().splitlines():
        country = line.strip()
        normalized_country = _normalize_name(country)
        if country and normalized_country not in seen_normalized:
            countries.append(country)
            seen_normalized.add(normalized_country)
    return countries


def _get_csv_column_name(fieldnames: Sequence[str], supported_names: tuple[str, ...], label: str) -> str:
    normalized_to_original = {_normalize_name(name): name for name in fieldnames}
    for supported_name in supported_names:
        normalized_supported = _normalize_name(supported_name)
        if normalized_supported in normalized_to_original:
            return normalized_to_original[normalized_supported]
    raise ValueError(f"Missing {label} column. Found columns: {fieldnames}")


def load_price_by_iso(price_csv_path: Path) -> dict[str, float]:
    max_price_by_iso: dict[str, float] = {}
    with price_csv_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        iso_column = _get_csv_column_name(fieldnames, ("ISO Country", "ISO code", "ISO", "Country ISO"), "ISO")
        price_column = _get_csv_column_name(fieldnames, ("Price ($USD)", "Price", "Rate", "SMS Price"), "price")
        for row in reader:
            iso_code = row[iso_column].strip()
            price = float(row[price_column])
            max_price_by_iso[iso_code] = max(max_price_by_iso.get(iso_code, 0.0), price)
    return max_price_by_iso


def load_features_by_name(feature_csv_path: Path) -> tuple[dict[str, FeatureCountry], dict[str, FeatureCountry]]:
    feature_by_norm_name: dict[str, FeatureCountry] = {}
    feature_by_iso: dict[str, FeatureCountry] = {}

    with feature_csv_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        iso_column = _get_csv_column_name(
            fieldnames,
            ("ISO code", "ISO Country", "ISO", "Country ISO", "ISO CODES", "ISO Codes"),
            "ISO",
        )
        country_column = _get_csv_column_name(
            fieldnames,
            ("Country or region", "Country", "Country Name", "Country or Region"),
            "country",
        )
        dialing_code_column = _get_csv_column_name(
            fieldnames,
            ("Dialing code", "Dial code", "Dialing prefix", "Country code", "COUNTRY CODE", "Prefix"),
            "dialing code",
        )
        for row in reader:
            iso_code = row[iso_column].strip()
            country_name = re.sub(r"\d+$", "", row[country_column]).strip()
            prefixes = _parse_prefixes(row[dialing_code_column])
            feature = FeatureCountry(country_name=country_name, iso_code=iso_code, prefixes=prefixes)
            feature_by_norm_name[_normalize_name(country_name)] = feature
            feature_by_iso[iso_code] = feature

    return feature_by_norm_name, feature_by_iso


def resolve_allowed_country(
    allowed_country: str,
    feature_by_norm_name: dict[str, FeatureCountry],
) -> FeatureCountry:
    normalized_allowed = _normalize_name(allowed_country)
    if normalized_allowed in feature_by_norm_name:
        return feature_by_norm_name[normalized_allowed]

    alias_name = ALLOW_NAME_ALIASES.get(normalized_allowed)
    if alias_name and alias_name in feature_by_norm_name:
        return feature_by_norm_name[alias_name]

    raise ValueError(f"Unable to map allow-list country '{allowed_country}' to AWS country prefix features")


def calculate_billable_units(price_usd: float, base_rate: float) -> int:
    if price_usd <= 0:
        raise ValueError(f"Price must be positive, got {price_usd}")
    if base_rate <= 0:
        raise ValueError(f"Base rate must be positive, got {base_rate}")
    return int(math.ceil(price_usd / base_rate))


def load_dlr_snapshot(snapshot_path: Path) -> dict[str, str | None]:
    with snapshot_path.open() as snapshot_file:
        snapshot_data = yaml.safe_load(snapshot_file) or {}
    return {str(prefix): value for prefix, value in snapshot_data.items()}


def build_dlr_snapshot(source_yaml_path: Path) -> dict[str, str | None]:
    with source_yaml_path.open() as source_file:
        source_data = yaml.safe_load(source_file) or {}

    snapshot = {}
    for prefix, values in source_data.items():
        attributes = values.get("attributes", {})
        snapshot[str(prefix)] = attributes.get("dlr")
    return snapshot


def write_yaml_file(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as output_file:
        yaml.safe_dump(data, output_file, sort_keys=False, allow_unicode=True, width=120)


def build_international_rates(
    allowed_countries: list[str],
    max_price_by_iso: dict[str, float],
    feature_by_iso: dict[str, FeatureCountry],
    dlr_snapshot: dict[str, str | None],
    base_rate: float,
    default_dlr: str | None,
) -> dict[str, dict]:
    entries_by_prefix: dict[str, dict] = {}
    names_by_prefix: dict[str, set[str]] = defaultdict(set)

    allowed_set = {iso.strip().upper() for iso in allowed_countries}

    # Iterate every country available in the feature set and compute
    # billable units when price data exist. Mark whether *we* can send to
    # the country via `we_can_send` attribute (based on allow-list).
    for iso, feature in feature_by_iso.items():
        iso_norm = (iso or "").strip().upper()
        if not iso_norm:
            continue

        price = max_price_by_iso.get(iso_norm)
        billable_units = None
        if price is not None:
            billable_units = calculate_billable_units(price, base_rate)

        for prefix in feature.prefixes:
            # preserve the special-case for North America country code
            if prefix == "1" and billable_units is not None:
                billable_units = 1

            names_by_prefix[prefix].add(feature.country_name)
            existing_entry = entries_by_prefix.get(prefix)

            # Resolve conflicting billable unit values by taking the max
            # when both sides provide a numeric value; otherwise prefer
            # whichever is numeric (None means price missing).
            resolved_units = billable_units
            if existing_entry:
                existing_units = existing_entry.get("billable_units")
                if existing_units is None:
                    resolved_units = billable_units
                elif billable_units is None:
                    resolved_units = existing_units
                else:
                    resolved_units = max(existing_units, billable_units)

            # If a prefix maps to multiple countries, merge attributes
            # instead of letting the last country overwrite previous values.
            existing_entry = entries_by_prefix.get(prefix)
            existing_we_can_send = False
            existing_dlr = None
            if existing_entry:
                existing_attrs = existing_entry.get("attributes", {})
                existing_we_can_send = bool(existing_attrs.get("we_can_send"))
                existing_dlr = existing_attrs.get("dlr")

            current_we_can_send = iso_norm in allowed_set
            merged_we_can_send = existing_we_can_send or current_we_can_send
            merged_dlr = existing_dlr if existing_dlr is not None else dlr_snapshot.get(prefix, default_dlr)

            entries_by_prefix[prefix] = {
                "attributes": {
                    "dlr": merged_dlr,
                    "we_can_send": merged_we_can_send,
                },
                "billable_units": resolved_units,
                "names": [],
            }

    ordered_prefixes = sorted(entries_by_prefix.keys(), key=lambda prefix: (int(prefix), prefix))
    output_data: dict[str, dict] = {}
    for prefix in ordered_prefixes:
        entry = entries_by_prefix[prefix]
        entry["names"] = sorted(names_by_prefix[prefix])
        output_data[prefix] = entry

    return output_data


def update_international_billing_rates(
    allow_list_path: Path,
    price_csv_path: Path,
    feature_csv_path: Path,
    dlr_snapshot_path: Path,
    output_path: Path,
    base_rate: float,
    default_dlr: str | None,
) -> dict[str, dict]:
    allowed_countries = load_allowed_countries(allow_list_path)
    max_price_by_iso = load_price_by_iso(price_csv_path)
    _, feature_by_iso = load_features_by_name(feature_csv_path)
    dlr_snapshot = load_dlr_snapshot(dlr_snapshot_path)

    updated_rates = build_international_rates(
        allowed_countries=allowed_countries,
        max_price_by_iso=max_price_by_iso,
        feature_by_iso=feature_by_iso,
        dlr_snapshot=dlr_snapshot,
        base_rate=base_rate,
        default_dlr=default_dlr,
    )
    write_yaml_file(updated_rates, output_path)
    return updated_rates


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update international billing rates from AWS CSVs")
    parser.add_argument(
        "--price-file",
        "-p",
        type=Path,
        default=DEFAULT_PRICES_PATH,
        help="Path to the AWS prices CSV file",
    )

    args = parser.parse_args(argv)

    update_international_billing_rates(
        allow_list_path=DEFAULT_ALLOW_LIST_PATH,
        price_csv_path=args.price_file,
        feature_csv_path=DEFAULT_PREFIX_FEATURES_PATH,
        dlr_snapshot_path=DEFAULT_DLR_SNAPSHOT_PATH,
        output_path=DEFAULT_OUTPUT_PATH,
        base_rate=DEFAULT_BASE_RATE,
        default_dlr=DEFAULT_DLR,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
