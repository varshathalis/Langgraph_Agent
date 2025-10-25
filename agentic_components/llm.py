# Load environment variables from .env
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from agentic_components.mcp_tools import get_builtin_tools

load_dotenv()

# Read from .env
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Initialize Azure OpenAI model via LangChain
_base_model = AzureChatOpenAI(
    openai_api_key=AZURE_API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    openai_api_version=AZURE_API_VERSION,
    model=AZURE_DEPLOYMENT_NAME,
    temperature=0.2,
)

# Get built-in tools and bind to model
_tools = get_builtin_tools()
model = _base_model.bind_tools(_tools)