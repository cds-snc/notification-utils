import subprocess
import json
import sys

# usage: AWS_PROFILE=notify-production python validate_phone_numbers.py numbers.txt
# numbers.txt should have one phone number per line.

# example Hasura query to get numbers.txt
#
#     select distinct "to"
#     from notifications
#     where service_id = '432cb269-7c85-4e38-8e42-3828ec7e5799'
#     and notification_status = 'temporary-failure'
#     and notification_type = 'sms'
#     and created_at > '2022-01-04'
#     order by created_at desc
#     limit 100


if __name__ == "__main__":
    filename = sys.argv[1]
    file = open(filename, "r")

    for number in file:
        number = number.strip()
        if number.startswith("+1"):
            query_number = number
        elif number.startswith("1"):
            query_number = "+" + number
        else:
            query_number = "+1" + number

        cmd = ["aws", "pinpoint", "phone-number-validate", "--number-validate-request", f"PhoneNumber={query_number}"]

        try:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, universal_newlines=True)
            output = process.stdout
            validate_response = json.loads(output)["NumberValidateResponse"]
            phoneType = validate_response["PhoneType"]
        except ValueError:
            phoneType = "--- validation error ---"
        print(f"{number}, {phoneType}")  # noqa: T001
    file.close()
