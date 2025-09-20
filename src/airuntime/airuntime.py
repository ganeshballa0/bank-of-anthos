# airruntime.py
import os
import jwt
import uuid
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# -------------------------------------------------------------------
# Configure Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Config from environment
# -------------------------------------------------------------------
APP_NAME = "banking_ai_runtime"
MODEL_ID = "gemini-2.0-flash"

PUBLIC_KEY = open(os.environ["PUB_KEY_PATH"], "r").read()
PROJECT_ID = os.environ.get("PROJECT_ID", "demo-project")
LOCATION = os.environ.get("LOCATION", "us-central1")

CONTACTS_API_ADDR = os.environ.get("CONTACTS_API_ADDR", "contacts:8080")
BALANCES_API_ADDR = os.environ.get("BALANCES_API_ADDR", "balancereader:8080")
HISTORY_API_ADDR = os.environ.get("HISTORY_API_ADDR", "transactionhistory:8080")
TRANSACTIONS_API_ADDR = os.environ.get("TRANSACTIONS_API_ADDR", "ledgerwriter:8080")

os.environ["GOOGLE_API_KEY"] = "AIzaSyDuu8EhcXrLt8SITFndRhMitxg41mSh_uQ"

CONTACTS_URL = f"http://{CONTACTS_API_ADDR}/contacts"
BALANCES_URL = f"http://{BALANCES_API_ADDR}/balances"
HISTORY_URL = f"http://{HISTORY_API_ADDR}/transactions"
TRANSACTIONS_URL = f"http://{TRANSACTIONS_API_ADDR}/transactions"

# -------------------------------------------------------------------
# Security
# -------------------------------------------------------------------
bearer_scheme = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """Validate JWT and return claims"""
    token = credentials.credentials
    try:
        claims = jwt.decode(
            jwt=token,
            key=PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_signature": True},
        )
        logger.info("JWT verified successfully. Claims: %s", claims)
        return claims
    except jwt.exceptions.InvalidTokenError as err:
        logger.error("Invalid JWT token: %s", str(err))
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(err)}")

# -------------------------------------------------------------------
# Tools
# -------------------------------------------------------------------
def get_contacts(username: str, token: str) -> dict:
    """Retrieve the contact list for a user."""
    logger.info("Fetching contacts for user: %s", username)
    try:
        resp = requests.get(f"{CONTACTS_URL}/{username}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as e:
        logger.error("Error fetching contacts: %s", e)
        return {"status": "error", "error_message": str(e)}

def add_contact(username: str, label: str, account_num: str, routing_num: str, token: str, is_external: bool = False) -> dict:
    """Add a new contact for the user."""
    logger.info("Adding contact for user %s: label=%s, account_num=%s, routing_num=%s, external=%s",
                username, label, account_num, routing_num, is_external)
    
    contact_payload = {
        "label": label,
        "account_num": account_num,
        "routing_num": routing_num,
        "is_external": is_external
    }

    try:
        resp = requests.post(
            f"{CONTACTS_URL}/{username}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=contact_payload,
            timeout=10
        )
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}

    except requests.HTTPError as e:
        logger.error("HTTP error adding contact: %s, response text: %s", e, getattr(e.response, "text", None))
        return {"status": "error", "error_message": str(e), "response": getattr(e.response, "text", None)}
    
    except Exception as e:
        logger.error("Unexpected error adding contact: %s", e)
        return {"status": "error", "error_message": str(e)}

def get_balance(account_id: str, token: str) -> dict:
    """Retrieve the account balance for a user."""
    logger.info("Fetching balance for account: %s", account_id)
    try:
        resp = requests.get(f"{BALANCES_URL}/{account_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as e:
        logger.error("Error fetching balance: %s", e)
        return {"status": "error", "error_message": str(e)}

def get_history(account_id: str, token: str) -> dict:
    """Retrieve transaction history for a user."""
    logger.info("Fetching history for account: %s", account_id)
    try:
        resp = requests.get(f"{HISTORY_URL}/{account_id}",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as e:
        logger.error("Error fetching history: %s", e)
        return {"status": "error", "error_message": str(e)}

def make_payment(from_account: str, to_account: str, amount: float, token: str) -> dict:
    """Submit a payment request to the ledgerwriter service."""
    from_routing = os.getenv("LOCAL_ROUTING_NUM", "883745000")
    to_routing = os.getenv("LOCAL_ROUTING_NUM", "883745000")
    
    payload = {
        "fromAccountNum": from_account,
        "fromRoutingNum": from_routing,
        "toAccountNum": to_account,
        "toRoutingNum": to_routing,
        "amount": int(amount * 100),
        "uuid": str(uuid.uuid4())
    }

    logger.info(
        "Making payment: from_account=%s, from_routing=%s, to_account=%s, to_routing=%s, amount_cents=%d, uuid=%s",
        from_account, from_routing, to_account, to_routing, payload["amount"], payload["uuid"]
    )

    try:
        resp = requests.post(
            TRANSACTIONS_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            data = resp.text
        logger.info("Payment request successful. Response: %s", data)
        return {"status": "success", "data": data}
    except requests.HTTPError as e:
        logger.error("HTTP error making payment: %s, response text: %s", e, getattr(e.response, "text", None))
        return {"status": "error", "error_message": str(e), "response": getattr(e.response, "text", None)}
    except Exception as e:
        logger.error("Unexpected error making payment: %s", e)
        return {"status": "error", "error_message": str(e)}

# -------------------------------------------------------------------
# Function Tools
# -------------------------------------------------------------------
contacts_tool = FunctionTool(func=get_contacts)
add_contact_tool = FunctionTool(func=add_contact)
balance_tool = FunctionTool(func=get_balance)
history_tool = FunctionTool(func=get_history)
payment_tool = FunctionTool(func=make_payment)

# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------
bank_agent = Agent(
    model=MODEL_ID,
    name="banking_agent",
    instruction=(
        "You are an intelligent banking assistant.\n"
        "- Use 'get_contacts' to fetch a user’s contact list.\n"
        "- Use 'add_contact' to add a new contact for the user.\n"
        "- Use 'get_balance' to fetch a user’s account balance.\n"
        "- Use 'get_history' to fetch transaction history.\n"
        "- Use 'make_payment' to transfer money between accounts.\n"
        "If no tool is required, just respond naturally."
    ),
    tools=[contacts_tool, add_contact_tool, balance_tool, history_tool, payment_tool],
)

# -------------------------------------------------------------------
# FastAPI Application
# -------------------------------------------------------------------
app = FastAPI(title="AI Banking Runtime")

class AskRequest(BaseModel):
    prompt: str

@app.get("/healthz")
def healthz():
    return JSONResponse({"status": "ok"})

@app.post("/ask")
async def ask_ai(request: AskRequest, claims: dict = Depends(verify_jwt)):
    """Handle user queries after JWT authentication with full logging."""
    user_id = claims.get("sub") or claims.get("username") or claims.get("user") or "unknown-user"
    account_id = claims.get("acct", "unknown-account")
    session_id = claims.get("session_id") or str(uuid.uuid4())

    logger.info("Received query from user: %s, session: %s", user_id, session_id)
    logger.info("Prompt: %s", request.prompt)

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    logger.info("Session created: %s", session_id)

    runner = Runner(agent=bank_agent, app_name=APP_NAME, session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=request.prompt)])
    final_answer = ""

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_answer += part.text
                        logger.info("Agent text part: %s", part.text)
            elif event.actions and getattr(event.actions, "escalate", False):
                final_answer = f"Agent escalated: {getattr(event, 'error_message', 'No specific message.')}"

            break

    logger.info("Final agent response: %s", final_answer)
    return {"answer": final_answer or "No response generated."}

# -------------------------------------------------------------------
# Run Uvicorn for container
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
