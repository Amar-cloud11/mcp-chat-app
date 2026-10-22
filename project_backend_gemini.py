
import json
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from models import ChatRequest, ChatResponse

# Load .env from this project's directory.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

MCP_SERVER_FILE = BASE_DIR / "server.py"

app = FastAPI(title="Gemini MCP Chat Capstone")

# Gemini is optional until a key is configured.
gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


def convert_tools(mcp_tools):
    """Convert MCP tool schemas to Gemini function declarations."""
    declarations = []

    for tool in mcp_tools:
        schema = dict(tool.inputSchema or {})
        schema.pop("$schema", None)

        # Gemini does not need MCP's descriptive schema metadata.
        schema.pop("title", None)

        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or tool.name,
                parameters_json_schema=schema,
            )
        )

    if not declarations:
        return []

    return [types.Tool(function_declarations=declarations)]


def mcp_result_to_text(result) -> str:
    """Convert the MCP tool response to readable text."""
    parts = []

    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))

    output = "\n".join(parts) or "The tool returned no text."

    if result.isError:
        return f"MCP tool error: {output}"

    return output


async def process_chat(query: str) -> str:
    if gemini_client is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is missing. Add it to the project's .env file."
            ),
        )

    if not MCP_SERVER_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"MCP server file not found: {MCP_SERVER_FILE}",
        )

    # Launch the existing MCP server through STDIO.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_FILE)],
        cwd=str(BASE_DIR),
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                mcp_response = await session.list_tools()
                gemini_tools = convert_tools(mcp_response.tools)

                contents = [
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=query)],
                    )
                ]

                # Limit repeated tool calls to avoid an endless loop.
                for _ in range(8):
                    config = types.GenerateContentConfig(
                        tools=gemini_tools or None,
                        automatic_function_calling=(
                            types.AutomaticFunctionCallingConfig(
                                disable=True
                            )
                        ),
                    )

                    response = await gemini_client.aio.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=contents,
                        config=config,
                    )

                    function_calls = response.function_calls or []

                    # Gemini answered directly without requesting a tool.
                    if not function_calls:
                        return response.text or "Gemini returned no text."

                    if not response.candidates:
                        return "Gemini returned no usable candidate."

                    # Preserve Gemini's tool-call message in conversation history.
                    contents.append(response.candidates[0].content)

                    for call in function_calls:
                        tool_name = call.name

                        # Only allow tools actually provided by the MCP server.
                        allowed_names = {
                            tool.name for tool in mcp_response.tools
                        }

                        if tool_name not in allowed_names:
                            tool_output = (
                                f"Rejected unknown MCP tool: {tool_name}"
                            )
                        else:
                            arguments = dict(call.args or {})

                            print(f"MCP tool selected: {tool_name}")
                            print(f"Tool arguments: {arguments}")

                            try:
                                result = await session.call_tool(
                                    tool_name,
                                    arguments=arguments,
                                )
                                tool_output = mcp_result_to_text(result)
                            except Exception as tool_error:
                                tool_output = (
                                    "Tool execution failed: "
                                    f"{type(tool_error).__name__}: "
                                    f"{tool_error}"
                                )

                            print(f"Tool result: {tool_output}")

                        # Return the actual tool result to Gemini.
                        function_response = types.Part.from_function_response(
                            name=tool_name,
                            response={"result": tool_output},
                            id=call.id,
                        )

                        contents.append(
                            types.Content(
                                role="user",
                                parts=[function_response],
                            )
                        )

                return (
                    "Stopped after 8 tool-call rounds. "
                    "Please try a simpler question."
                )

    except HTTPException:
        raise
    except Exception as error:
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=(
                f"Gemini/MCP failed: {type(error).__name__}: {error}"
            ),
        ) from error


@app.get("/")
async def home():
    return {
        "status": "ok",
        "application": "Gemini MCP Chat Capstone",
        "model": GEMINI_MODEL,
        "genai_enabled": gemini_client is not None,
    }


@app.get("/health")
async def health():
    return {
        "api": "running",
        "transport": "STDIO",
        "genai_enabled": gemini_client is not None,
        "model": GEMINI_MODEL,
        "mcp_server_file_exists": MCP_SERVER_FILE.exists(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="The query cannot be empty.",
        )

    answer = await process_chat(query)
    return ChatResponse(answer=answer)
