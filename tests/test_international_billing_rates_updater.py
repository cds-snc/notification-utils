import pytest
from notifications_utils.international_billing_rates_updater import (
    DEFAULT_ALLOW_LIST_PATH,
    DEFAULT_DLR_SNAPSHOT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PREFIX_FEATURES_PATH,
    DEFAULT_PRICES_PATH,
    FeatureCountry,
    build_international_rates,
    calculate_billable_units,
    load_allowed_countries,
    load_features_by_name,
    load_price_by_iso,
)


def test_calculate_billable_units_can_exceed_three():
    assert calculate_billable_units(0.31384, 0.02065) == 16


def test_load_allowed_countries_deduplicates_entries(tmp_path):
    allow_list = tmp_path / "country_list.txt"
    allow_list.write_text("Canada\nUnited States\nCanada\n")

    assert load_allowed_countries(allow_list) == ["Canada", "United States"]


def test_loaders_support_changed_column_names(tmp_path):
    prices_csv = tmp_path / "prices.csv"
    prices_csv.write_text("ISO,Country Name,Rate\n" "CA,Canada,0.007\n" "US,United States,0.008\n")

    prefixes_csv = tmp_path / "prefixes.csv"
    prefixes_csv.write_text("Country,ISO,Dial code\n" "Canada,CA,1\n" "United States,US,1\n")

    max_price_by_iso = load_price_by_iso(prices_csv)
    feature_by_name, _ = load_features_by_name(prefixes_csv)

    assert max_price_by_iso == {"CA": 0.007, "US": 0.008}
    assert "canada" in feature_by_name
    assert "united states" in feature_by_name


def test_build_international_rates_fails_on_conflicting_shared_prefix_when_strategy_fail(tmp_path):
    allowed_countries = ["Guernsey", "Jersey"]
    max_price_by_iso = {"GG": 0.08, "JE": 0.2}
    feature_by_name = {
        "guernsey": FeatureCountry(country_name="Guernsey", iso_code="GG", prefixes=("44",)),
        "jersey": FeatureCountry(country_name="Jersey", iso_code="JE", prefixes=("44",)),
    }

    with pytest.raises(ValueError, match="Conflicting billable_units"):
        build_international_rates(
            allowed_countries=allowed_countries,
            max_price_by_iso=max_price_by_iso,
            feature_by_norm_name=feature_by_name,
            dlr_snapshot={"1": "Carrier DLR"},
            base_rate=0.02065,
            default_dlr="YES",
            shared_prefix_strategy="fail",
        )


def test_build_international_rates_uses_max_on_shared_prefix_when_strategy_max(tmp_path):
    allowed_countries = ["Canada", "United States"]
    max_price_by_iso = {"CA": 0.02183, "US": 0.007}

    prefixes_csv = tmp_path / "prefixes.csv"
    prefixes_csv.write_text("Country or region,ISO code,Dialing code\n" "Canada,CA,1\n" "United States,US,1\n")
    feature_by_name, _ = load_features_by_name(prefixes_csv)

    rates = build_international_rates(
        allowed_countries=allowed_countries,
        max_price_by_iso=max_price_by_iso,
        feature_by_norm_name=feature_by_name,
        dlr_snapshot={"1": "Carrier DLR"},
        base_rate=0.02065,
        default_dlr="YES",
        shared_prefix_strategy="max",
    )

    assert set(rates.keys()) == {"1"}
    assert rates["1"]["billable_units"] == 1
    assert rates["1"]["attributes"] == {"dlr": "Carrier DLR"}
    assert rates["1"]["names"] == ["Canada", "United States"]


def test_default_paths_point_to_expected_files():
    assert DEFAULT_ALLOW_LIST_PATH.name == "country_list.txt"
    assert DEFAULT_PRICES_PATH.name == "aws_prices_sms.csv"
    assert DEFAULT_PREFIX_FEATURES_PATH.name == "country_prefixes.csv"
    assert DEFAULT_DLR_SNAPSHOT_PATH.name == "dlr_snapshot.yml"
    assert DEFAULT_OUTPUT_PATH.name == "international_billing_rates.yml"
