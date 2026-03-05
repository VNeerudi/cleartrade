import os
from typing import Any, Dict

import httpx
from mcp.server.fastmcp import FastMCP


BACKEND_API_BASE = os.getenv("CLEARTRADE_BACKEND_API", "http://127.0.0.1:8000/api")

mcp = FastMCP("ClearTrade MCP Server", json_response=True)


def _make_client() -> httpx.Client:
    return httpx.Client(base_url=BACKEND_API_BASE, timeout=30.0)


@mcp.tool()
def analyze_ticker(ticker: str) -> Dict[str, Any]:
    """
    Run ClearTrade's full pipeline (technical, fundamental, sentiment) for a stock ticker.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {"error": "ticker is required"}

    try:
        with _make_client() as client:
            resp = client.get("/analyze", params={"ticker": ticker})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"error": f"backend request failed: {exc}"}


@mcp.tool()
def chat_about_ticker(ticker: str, question: str) -> Dict[str, Any]:
    """
    Ask follow-up questions about the latest recommendation for a ticker
    (e.g., 'Why?', 'Confidence?', 'RSI?', 'Sentiment?').
    """
    ticker = (ticker or "").upper().strip()
    question = (question or "").strip()
    if not ticker or not question:
        return {"error": "ticker and question are required"}

    try:
        with _make_client() as client:
            resp = client.post("/chat", json={"ticker": ticker, "question": question})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"error": f"backend request failed: {exc}"}


@mcp.tool()
def get_ticker_history(ticker: str) -> Dict[str, Any]:
    """
    Get recent ClearTrade recommendation history for a stock ticker.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {"error": "ticker is required"}

    try:
        with _make_client() as client:
            resp = client.get("/history", params={"ticker": ticker})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        return {"error": f"backend request failed: {exc}"}


if __name__ == "__main__":
    # Default to Streamable HTTP on the standard MCP Inspector endpoint:
    # MCP endpoint: http://127.0.0.1:8000/mcp
    # Run the Django backend on a different port (e.g. 8002) to avoid conflicts.
    mcp.run(transport="streamable-http")

