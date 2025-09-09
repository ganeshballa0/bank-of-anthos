# ai_runtime.py
from google.cloud import aiplatform
from mcp.client import Client

# Initialize Vertex AI client
aiplatform.init(project="bank-of-anthos-470616", location="us-central1")
mcp_client = Client("http://localhost:8000")  # MCP server address (same pod or service)

def ask_ai(prompt: str, username: str, token: str) -> str:
    """
    Sends the prompt to Gemini, allowing it to call MCP tools.
    The tools available are described in the prompt.
    """
    full_prompt = f"""
You are an intelligent banking assistant with access to tools:
1. login(username, password)
2. get_contacts(username, token)

Respond to the user request: {prompt}
"""
    # Call the Gemini chat model with automatic function calling enabled
    response = aiplatform.ChatModel.from_pretrained("gemini-1").predict(
        contents=full_prompt,
        config=aiplatform.types.GenerateContentConfig(
            tools=[mcp_client],  # allows the model to call MCP tools
            temperature=0.7
        )
    )
    return response.text
