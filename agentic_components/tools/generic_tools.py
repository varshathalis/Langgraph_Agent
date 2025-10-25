"""
Generic Tools for Conversational Handling
----------------------------------------
Includes a single tool for greeting detection and response.
"""

import json
import os
from typing import Optional
from fastmcp import FastMCP
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from  dotenv import load_dotenv
load_dotenv()



def register_tools(mcp: FastMCP):
    """Register general-purpose conversational tools."""

    # ----------------------------------------------------------------------
    # GREETING HANDLER TOOL
    # ----------------------------------------------------------------------
    @mcp.tool()
    async def handle_greeting(
        text: str,
        openai_api_key: str,
        user_name: Optional[str] = None,
    ) -> str:
        """
        Detects if the user message is a greeting (like 'hi', 'hello', 'good morning')
        and returns a friendly, human-like response.
        """
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "yo", "what’s up"]
        lower_text = text.lower().strip()

        OPENAI_MODEL = os.getenv("OPENAI_MODEL")

        # --- Greeting Detection ---
        if not any(word in lower_text for word in greetings):
            return "No greeting detected."

        # --- Generate Natural Response ---
        try:
            llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.6, api_key=openai_api_key)
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a friendly AI assistant that replies to greetings warmly and naturally."
                ),
                (
                    "user",
                    f"User{' ' + user_name if user_name else ''} said: '{text}'. Reply naturally and kindly in one short sentence."
                ),
            ])

            chain = prompt | llm | StrOutputParser()
            result = await chain.ainvoke({})
            return result.strip()

        except Exception as e:
            return f"⚠️ Failed to process greeting: {str(e)}"

    print("✅ Generic greeting tool registered successfully.")
