from google.cloud import aiplatform
from mcp.client import Client

# 1️⃣ Initialize MCP client pointing to your MCP microservice
mcp_client = Client("http://localhost:8000")  # Replace with your MCP microservice URL

# 2️⃣ Initialize Vertex AI client
aiplatform.init(project="YOUR_GCP_PROJECT", location="us-central1")

# 3️⃣ Your LLM function using Gemini
def ask_ai(prompt: str):
    """
    Sends prompt to Vertex AI Gemini and allows it to call MCP tools.
    """
    # Here, tools are exposed via MCP client
    # For demo, assume your MCP client exposes 'login' and 'get_contacts'
    
    # Example prompt to AI
    full_prompt = f"""
    You are an intelligent assistant. You have the following tools:
    1. login(username, password)
    2. get_contacts(username, token)

    Answer the following user request: {prompt}
    """

    # Send prompt to Vertex AI
    response = aiplatform.ChatModel.from_pretrained("gemini-1").predict(
        full_prompt
    )
    return response.text

# 4️⃣ Example usage
if __name__ == "__main__":
    # Ask AI to retrieve Alice's contacts
    result = ask_ai("Log in as 'alice' and show my saved contacts")
    print(result)
