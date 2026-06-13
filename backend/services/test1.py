import requests

response = requests.post(
    "https://api.digikey.com/v1/oauth2/token",
    data={
        "code": "GVYgKPRB",
        "client_id": "OiGPzr1YRGtkbUGmbpMbiiG5khCu6MX0Dc5XUnnqjqEBh4gh",
        "client_secret": "IcOxf90Bmw4xi2ujUCuAB3NNxBFm9nzKUumddA1IzBSeL388MOBufEWJfflglqcG",
        "redirect_uri": "https://localhost",
        "grant_type": "authorization_code",
    }
)
print(response.json())