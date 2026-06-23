import requests

print("Sandbox working perfectly!")

# A quick public API test to prove we can make web requests
try:
    response = requests.get("https://api.github.com")
    print(f"Connection test to GitHub API: Status Code {response.status_code} (Success!)")
    print("Ready to start building the World Cup data engine.")
except Exception as e:
    print(f"Something went wrong with the connection: {e}")