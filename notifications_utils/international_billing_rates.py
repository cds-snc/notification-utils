"""
Format of the yaml file looks like:

1:
  attributes:
    alpha: 'NO'
    comment: null
    dlr: Carrier DLR
    generic_sender: ''
    numeric: LIMITED
    sc: 'NO'
    sender_and_registration_info: All senders CONVERTED into random long numeric senders
    text_restrictions: Bulk/marketing traffic NOT allowed
  billable_units: 1
  names:
  - Canada
  - United States
  - Dominican Republic
"""

import csv
import os

import yaml

dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/international_billing_rates.yml".format(dir_path)) as f:
    INTERNATIONAL_BILLING_RATES = yaml.safe_load(f)
    COUNTRY_PREFIXES = list(reversed(sorted(INTERNATIONAL_BILLING_RATES.keys(), key=len)))


def export_multipliers_csv(output_path="international_billing_rates_multipliers.csv"):
    """
    Write a CSV file containing the billing multipliers for all countries
    that can be sent to (i.e. where can_send is true).

    Columns: country, country_code, rate_multiplier
    """
    rows = []
    for prefix, entry in INTERNATIONAL_BILLING_RATES.items():
        if entry.get("attributes", {}).get("can_send"):
            multiplier = entry["billable_units"]
            for country in entry.get("names", []):
                rows.append({"country": country, "country_code": prefix, "rate_multiplier": multiplier})

    rows.sort(key=lambda r: r["country"])

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["country", "country_code", "rate_multiplier"])
        writer.writeheader()
        writer.writerows(rows)

    return output_path
