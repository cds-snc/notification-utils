# SMS pricing updater

This folder contains source files and tooling to regenerate:

- `notifications_utils/international_billing_rates.yml`

from:

- `scripts/sms_pricing/allowed_country_list.csv` (countries we allow sending to)
- `scripts/sms_pricing/aws_prices_sms_mar_2026.csv` (AWS SMS price export)
- `scripts/sms_pricing/country_prefixes.csv` (country/ISO/prefix export)

## Rules currently implemented

- `billable_units` is a rate multiplier calculated as:
  - `ceil(price / base_rate)`
  - If prefix is '1' (North America), always set to `1`
- `base_rate` default is `0.01507`
- YAML `attributes` include:
  - `dlr` — from snapshot or default
  - `can_send` — `true` if ISO is in allow-list, `false` otherwise
- DLR values are preserved from a snapshot file:
  - `scripts/sms_pricing/dlr_snapshot.yml`
- If DLR is missing in snapshot for a new prefix, default is:
  - `YES`

## Run updater

From repo root, run the Makefile target with the price CSV file:

```bash
make update-rates PRICE_FILE=scripts/sms_pricing/aws_prices_sms_mar_2026.csv
```

The updater will:
1. Load allowed ISOs from `allowed_country_list.csv`
2. Parse prices and country names from the provided price CSV
3. Load prefix-to-dialing-code mappings from `country_prefixes.csv`
4. Build the YAML, mapping each ISO to its prefix(es) and setting `can_send` based on the allow-list
5. Write to `notifications_utils/international_billing_rates.yml`

To use a different price CSV, pass it as `PRICE_FILE`. Otherwise, the default (`aws_prices_sms_mar_2026.csv`) is used.

If defaults (base rate, DLR, paths) need to change, edit the constants at the top of:
- `scripts/sms_pricing/international_billing_rates_updater.py`

## Updating rates later

When AWS rates change:

1. Download the latest rates file from AWS:
  - `https://aws.amazon.com/end-user-messaging/pricing/`
2. Save the export. The script expects headers exactly:
  - `ISO Country` — ISO code
  - `Price ($USD)` — price in USD
  - `Country Name` (optional) — country name; if present, it's used in the YAML
  - Other columns (e.g., `CarrierName`, `Number Type`) are ignored
3. If headers don't match, normalize the CSV first.
4. Run:
  ```bash
  make update-rates PRICE_FILE=/path/to/new_prices.csv
  ```

## Shared-prefix conflicts

When multiple countries resolve to the same dialing prefix but have different computed multipliers,
the updater uses the maximum multiplier.

## Refreshing DLR snapshot

If you need to rebuild `dlr_snapshot.yml`, run the Makefile target from the repo root:

```bash
make refresh-dlr-snapshot
```

## Validation checklist

- run targeted tests:
  - `pytest tests/test_international_billing_rates.py tests/test_international_billing_rates_updater.py`
- review YAML diff for:
  - unexpected country removals
  - unexpected multiplier jumps
  - missing `dlr`
- if input CSV columns change, update the column aliases in:
  - `scripts/sms_pricing/international_billing_rates_updater.py`