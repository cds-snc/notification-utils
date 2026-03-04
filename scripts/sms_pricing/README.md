# SMS pricing updater

This folder contains source files and tooling to regenerate:

- `notifications_utils/international_billing_rates.yml`

from:

- `scripts/sms_pricing/country_list.txt` (countries we allow sending to)
- `scripts/sms_pricing/aws_prices_sms.csv` (AWS SMS price export)
- `scripts/sms_pricing/country_prefixes.csv` (country/ISO/prefix export)

## Rules currently implemented

- `billable_units` is a rate multiplier calculated as:
  - `ceil(price / base_rate)`
- `base_rate` default is `0.02065`
- YAML `attributes` is reduced to:
  - `dlr`
- DLR values are preserved from a snapshot file:
  - `scripts/sms_pricing/dlr_snapshot.yml`
- If DLR is missing in snapshot for a new prefix, default is:
  - `YES`

## Run updater

From repo root:

```bash
/home/vscode/.venv/workspace/bin/python notifications_utils/international_billing_rates_updater.py
```

This command now uses sensible defaults for all input/output file paths.

If defaults ever need to change, edit the constants at the top of:

- `notifications_utils/international_billing_rates_updater.py`

## Shared-prefix conflicts

When multiple countries resolve to the same dialing prefix but have different computed multipliers,
the updater uses the maximum multiplier.

## Refreshing DLR snapshot

If you need to rebuild `dlr_snapshot.yml`, run this one-off Python snippet from repo root:

```bash
python3 - <<'PY'
from notifications_utils.international_billing_rates_updater import (
    DEFAULT_DLR_SNAPSHOT_PATH,
    DEFAULT_OUTPUT_PATH,
    build_dlr_snapshot,
    write_yaml_file,
)

write_yaml_file(build_dlr_snapshot(DEFAULT_OUTPUT_PATH), DEFAULT_DLR_SNAPSHOT_PATH)
PY
```

## Validation checklist

- run targeted tests:
  - `pytest tests/test_international_billing_rates.py tests/test_international_billing_rates_updater.py`
- review YAML diff for:
  - unexpected country removals
  - unexpected multiplier jumps
  - missing `dlr`
- if input CSV columns change, update the column aliases in:
  - `notifications_utils/international_billing_rates_updater.py`