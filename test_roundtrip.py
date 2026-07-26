import json
import tomllib

with open("firebase-service-account.json", "r") as f:
    original = json.load(f)

with open("secrets_output.txt", "rb") as f:
    parsed_toml = tomllib.load(f)

reconstructed_key = parsed_toml["firebase_service_account"]["private_key"]
original_key = original["private_key"]

print("Match exactly:", reconstructed_key == original_key)
print("Original length:", len(original_key))
print("Reconstructed length:", len(reconstructed_key))

if reconstructed_key != original_key:
    for i, (a, b) in enumerate(zip(original_key, reconstructed_key)):
        if a != b:
            print(f"First diff at position {i}: original={a!r} reconstructed={b!r}")
            break