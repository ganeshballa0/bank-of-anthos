# airuntime.py
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
os.environ["GOOGLE_API_KEY"] = "AIzaSyDuu8EhcXrLt8SITFndRhMitxg41mSh_uQ" 

# Construct contacts URL dynamically
CONTACTS_URL = f"http://{CONTACTS_API_ADDR}/contacts"

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
    """Retrieve the contact list for a user (requires JWT token)."""
    logger.info("Fetching contacts for user: %s", username)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{CONTACTS_URL}/{username}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as e:
        logger.error("Error fetching contacts: %s", e)
        return {"status": "error", "error_message": str(e)}

contacts_tool = FunctionTool(func=get_contacts)

# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------
bank_agent = Agent(
    model=MODEL_ID,
    name="banking_agent",
    instruction=(
        "You are an intelligent banking assistant.\n"
        "- Use 'get_contacts' to fetch a user’s contact list.\n"
        "If no tool is required, just respond naturally."
    ),
    tools=[contacts_tool],
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
    session_id = claims.get("session_id") or str(uuid.uuid4())

    logger.info("Received query from user: %s, session: %s", user_id, session_id)
    logger.info("Prompt: %s", request.prompt)

    # Create session
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    logger.info("Session created: %s", session_id)

    # Run agent
    runner = Runner(agent=bank_agent, app_name=APP_NAME, session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=request.prompt)])
    final_answer = ""

    # Run agent asynchronously and concatenate all text parts
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
