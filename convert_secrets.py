import json

with open("firebase-service-account.json", "r") as f:
    data = json.load(f)

print("[firebase_service_account]")
for key, value in data.items():
    # Escape backslashes first, then quotes, then convert real newlines to literal \n
    value_escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    print(f'{key} = "{value_escaped}"')