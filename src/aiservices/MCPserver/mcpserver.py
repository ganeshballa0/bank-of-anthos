# mcpserver.py
from mcp.server import Server
import requests

server = Server("bank-ai")

@server.tool()
def login(username: str, password: str):
    """Login a user and return auth info (includes JWT)."""
    resp = requests.get("http://userservice:5000/login",
                        params={"username": username, "password": password})
    return resp.json()

@server.tool()
def get_contacts(username: str, token: str):
    """Retrieve the contact list for a user (requires JWT token)."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"http://contacts:5000/contacts/{username}", headers=headers)
    return resp.json()

if __name__ == "__main__":
    server.run()  # listens (default port 8000)
