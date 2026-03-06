from scripts.sms_pricing.international_billing_rates_updater import (
    DEFAULT_ALLOW_LIST_PATH,
    DEFAULT_DLR_SNAPSHOT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PREFIXES_PATH,
    DEFAULT_PRICES_PATH,
    CountryPrefix,
    build_international_rates,
    calculate_billable_units,
    load_allowed_countries,
    load_prefixes_by_name,
    load_price_by_iso,
)


def test_calculate_billable_units_can_exceed_three():
    assert calculate_billable_units(0.31384, 0.02065) == 16


def test_load_allowed_countries_deduplicates_entries(tmp_path):
    allow_list = tmp_path / "allowed_country_list.txt"
    allow_list.write_text("Canada\nUnited States\nCanada\n")

    assert load_allowed_countries(allow_list) == ["Canada", "United States"]


def test_loaders_support_changed_column_names(tmp_path):
    prices_csv = tmp_path / "prices.csv"
    prices_csv.write_text("ISO,Country Name,Rate\n" "CA,Canada,0.007\n" "US,United States,0.008\n")

    prefixes_csv = tmp_path / "prefixes.csv"
    prefixes_csv.write_text("COUNTRY,ISO_CODE,DIALING_CODE\n" "Canada,CA,1\n" "United States,US,1\n")

    max_price_by_iso = load_price_by_iso(prices_csv)
    prefix_by_name, _ = load_prefixes_by_name(prefixes_csv)

    assert max_price_by_iso == {"CA": 0.007, "US": 0.008}
    assert "canada" in prefix_by_name
    assert "united states" in prefix_by_name


def test_shared_prefix_max_resolution_guernsey_jersey(tmp_path):
    # With ISO-only allow-list and iso-indexed features, conflicting
    # numeric billable units should be resolved by taking the max.
    allowed_countries = ["GG", "JE"]
    max_price_by_iso = {"GG": 0.08, "JE": 0.2}
    feature_by_iso = {
        "GG": CountryPrefix(country_name="Guernsey", iso_code="GG", prefixes=("44",)),
        "JE": CountryPrefix(country_name="Jersey", iso_code="JE", prefixes=("44",)),
    }

    rates = build_international_rates(
        allowed_countries=allowed_countries,
        max_price_by_iso=max_price_by_iso,
        prefix_by_iso=feature_by_iso,
        dlr_snapshot={"1": "Carrier DLR"},
        base_rate=0.02065,
        default_dlr="YES",
    )

    assert set(rates.keys()) == {"44"}
    # GG -> ceil(0.08/0.02065)=4, JE -> ceil(0.2/0.02065)=10 -> max=10
    assert rates["44"]["billable_units"] == 10
    # No explicit dlr snapshot for prefix '44' was provided, so expect
    # the default DLR value to be used.
    assert rates["44"]["attributes"] == {"dlr": "YES", "can_send": True}
    assert rates["44"]["names"] == ["Guernsey", "Jersey"]


def test_build_international_rates_uses_max_on_shared_prefix_when_strategy_max(tmp_path):
    allowed_countries = ["CA", "US"]
    max_price_by_iso = {"CA": 0.02183, "US": 0.007}

    prefixes_csv = tmp_path / "prefixes.csv"
    prefixes_csv.write_text("COUNTRY,ISO_CODE,DIALING_CODE\n" "Canada,CA,1\n" "United States,US,1\n")
    prefix_by_name, feature_by_iso = load_prefixes_by_name(prefixes_csv)

    rates = build_international_rates(
        allowed_countries=allowed_countries,
        max_price_by_iso=max_price_by_iso,
        prefix_by_iso=feature_by_iso,
        dlr_snapshot={"1": "Carrier DLR"},
        base_rate=0.02065,
        default_dlr="YES",
    )

    assert set(rates.keys()) == {"1"}
    assert rates["1"]["billable_units"] == 1
    assert rates["1"]["attributes"] == {"dlr": "Carrier DLR", "can_send": True}
    assert rates["1"]["names"] == ["Canada", "United States"]


def test_default_paths_point_to_expected_files():
    assert DEFAULT_ALLOW_LIST_PATH.name == "allowed_country_list.csv"
    assert DEFAULT_PRICES_PATH.name == "aws_prices_sms_mar_2026.csv"
    assert DEFAULT_PREFIXES_PATH.name == "country_prefixes.csv"
    assert DEFAULT_DLR_SNAPSHOT_PATH.name == "dlr_snapshot.yml"
    assert DEFAULT_OUTPUT_PATH.name == "international_billing_rates.yml"
