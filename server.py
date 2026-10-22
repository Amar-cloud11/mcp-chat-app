
from mcp.server.fastmcp import FastMCP
import requests

# Create the MCP server
mcp = FastMCP("Capstone Tools")


@mcp.tool()
def get_weather(city: str) -> str:
    """Get example weather information for a city."""
    return f"The weather in {city} is hot and dry."


@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return their sum."""
    return a + b


@mcp.tool()
def get_capstone_info() -> str:
    """Explain what this MCP capstone project demonstrates."""
    return (
        "This capstone demonstrates an AI chat application "
        "using OpenAI, an MCP server, FastAPI, and Streamlit."
    )


@mcp.tool()
def get_cryptocurrency_price(crypto: str) -> str:
    """Get a cryptocurrency price in USD.

    Args:
        crypto: CoinGecko ID, such as bitcoin or ethereum.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": crypto.lower(),
        "vs_currencies": "usd"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        price = data.get(crypto.lower(), {}).get("usd")

        if price is not None:
            return f"The price of {crypto} is ${price:,.2f} USD."

        return f"Price for {crypto} was not found."

    except requests.RequestException as e:
        return f"Error fetching price: {e}"


# Tool 1: Add a note to the file
@mcp.tool()
def add_note_to_file(content: str) -> str:
    """
    Append a note to the user's local notes file.

    Args:
        content: The text content to save.
    """
    filename = "notes.txt"

    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(content + "\n")

        return f"Content appended to {filename}."

    except OSError as e:
        return f"Error appending to file {filename}: {e}"


# Tool 2: Read all saved notes
@mcp.tool()
def read_notes() -> str:
    """
    Read and return the contents of the local notes file.
    """
    filename = "notes.txt"

    try:
        with open(filename, "r", encoding="utf-8") as f:
            notes = f.read()

        return notes if notes.strip() else "No notes found."

    except FileNotFoundError:
        return "No notes file found. Add a note first."

    except OSError as e:
        return f"Error reading file {filename}: {e}"

# ______________________________________________________
#            resources
# _______________________________________________


# Sample inventory data
inventory_id_to_price = {
    "123": "6.99",
    "456": "17.99",
    "789": "84.99"
}

inventory_name_to_id = {
    "Coffee": "123",
    "Tea": "456",
    "Cookies": "789"
}


# Resource 1: Get inventory overview
@mcp.resource("inventory://overview")
def get_inventory_overview() -> str:
    """Returns an overview of inventory."""

    overview = """
    Inventory Overview:
    - Coffee
    - Tea
    - Cookies
    """

    return overview.strip()


# Resource 2: Get price using inventory ID
@mcp.resource("inventory://{inventory_id}/price")
def get_inventory_price_from_inventory_id(
    inventory_id: str
) -> str:
    """Returns the price for an inventory ID."""

    return inventory_id_to_price.get(
        inventory_id,
        "Inventory ID not found"
    )


# Resource 3: Get inventory ID using inventory name
@mcp.resource("inventory://{inventory_name}/id")
def get_inventory_id_from_inventory_name(
    inventory_name: str
) -> str:
    """Returns the ID for an inventory name."""

    return inventory_name_to_id.get(
        inventory_name,
        "Inventory name not found"
    )

# ______________________________________________
# prompts
# ________________________________________________


# Prompt 1: Detailed topic analysis
@mcp.prompt()
def get_prompt(topic: str) -> str:
    """
    Returns a prompt for detailed analysis of a topic.

    Args:
        topic: The topic to research.
    """
    return f"Do a detailed analysis on the following topic: {topic}"


# Prompt 2: Write a detailed historical report
@mcp.prompt()
def write_detailed_historical_report(
    topic: str,
    number_of_paragraphs: int
) -> str:
    """
    Creates a detailed historical research report prompt.

    Args:
        topic: The topic to research.
        number_of_paragraphs: Number of paragraphs in the main section.
    """
    prompt = """
Create a concise research report on the history of {topic}.

The report should contain 3 sections:
INTRODUCTION, MAIN, and CONCLUSION.

The MAIN section should be {number_of_paragraphs} paragraphs long.
Include a timeline of key events.
The conclusion should be in bullet-point format.
"""

    return prompt.format(
        topic=topic,
        number_of_paragraphs=number_of_paragraphs
    )


if __name__ == "__main__":
    mcp.run()
