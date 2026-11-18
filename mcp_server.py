
import os
from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", 8000))

app = FastMCP(
    "ClipMate AI",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True
)

@app.tool()
def get_project_status() -> dict:
    """Check ClipMate AI project status."""
    return {
        "name": "ClipMate AI",
        "status": "Under development",
        "features": [
            "Video information",
            "Clip detection",
            "Clip exporting",
            "Caption generation",
            "Vertical video formatting"
        ]
    }

if __name__ == "__main__":
    app.run(transport="streamable-http")

