import subprocess
import json
import sys

# usage: AWS_PROFILE=notify-production python validate_phone_numbers.py numbers.txt
# numbers.txt should have one phone number per line.
# NOTE: there is a fee for each number, approximately $0.02. Consider this before running a large query.

# example Hasura query to get numbers.txt
#
#     select distinct normalised_to
#     from notifications
#     where service_id = '432cb269-7c85-4e38-8e42-3828ec7e5799'
#     and notification_status = 'temporary-failure'
#     and notification_type = 'sms'
#     limit 10


if __name__ == "__main__":
    filename = sys.argv[1]
    file = open(filename, "r")

    for number in file:
        number = number.strip()
        cmd = ["aws", "pinpoint", "phone-number-validate", "--number-validate-request", f"PhoneNumber={number}"]
        try:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, universal_newlines=True)
            output = process.stdout
            validate_response = json.loads(output)["NumberValidateResponse"]
            phoneType = validate_response["PhoneType"]
        except ValueError:
            phoneType = "--- validation error ---"
        print(f"{number}, {phoneType}")  # noqa: T001
    file.close()
