
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from models import ChatRequest, ChatResponse

BASE_DIR = Path(__file__).resolve().parent
MCP_SERVER_FILE = BASE_DIR / "server.py"

app = FastAPI(title="MCP Chat Capstone - No GenAI")


def choose_tool(query: str, tools: list):
    q = query.lower()

    if any(word in q for word in ["weather", "temperature", "forecast"]):
        keywords = ["weather"]
    elif any(word in q for word in [
        "crypto", "bitcoin", "ethereum", "coin price"
    ]):
        keywords = ["crypto", "bitcoin", "price"]
    else:
        return None

    for tool in tools:
        description = f"{tool.name} {tool.description or ''}".lower()
        if any(word in description for word in keywords):
            return tool

    return None


def make_arguments(tool, query: str) -> dict:
    schema = tool.inputSchema or {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    args = {}
    q = query.lower()

    import re
    match = re.search(r"\bin\s+([a-zA-Z][a-zA-Z .-]*)", query)
    place = match.group(1).strip(" ?.!,") if match else "Chennai"

    for field in properties:
        name = field.lower()

        if any(word in name for word in ["city", "location", "place"]):
            args[field] = place
        elif any(word in name for word in [
            "symbol", "coin", "crypto", "currency"
        ]):
            args[field] = (
                "ethereum" if "ethereum" in q else "bitcoin"
            )
        elif field in required:
            raise ValueError(
                f"Tool '{tool.name}' needs argument '{field}'. "
                "Configure its argument mapping before calling it."
            )

    missing = [field for field in required if field not in args]
    if missing:
        raise ValueError(
            f"Missing required arguments for {tool.name}: {missing}"
        )

    return args


def result_to_text(result) -> str:
    output = "\n".join(
        item.text if hasattr(item, "text") else str(item)
        for item in result.content
    )

    if result.isError:
        return f"MCP tool error: {output}"

    return output or "The tool returned no text."


async def process_chat(query: str) -> str:
    if not MCP_SERVER_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"MCP server file not found: {MCP_SERVER_FILE}",
        )

    # Launch server.py as an MCP STDIO subprocess.
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_FILE)],
        cwd=str(BASE_DIR),
    )

    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.list_tools()

                tool = choose_tool(query, response.tools)

                if tool is None:
                    names = ", ".join(item.name for item in response.tools)
                    return (
                        "I could not match your question to a tool. "
                        f"Available tools: {names}. "
                        "Try asking about weather or crypto."
                    )

                arguments = make_arguments(tool, query)
                result = await session.call_tool(
                    tool.name, arguments=arguments
                )
                return result_to_text(result)

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"MCP STDIO request failed: "
                   f"{type(error).__name__}: {error}",
        ) from error


@app.get("/")
async def home():
    return {
        "status": "ok",
        "mode": "No GenAI API",
        "transport": "STDIO",
    }


@app.get("/health")
async def health():
    return {
        "api": "running",
        "genai_enabled": False,
        "transport": "STDIO",
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
