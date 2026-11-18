
from mcp.server.fastmcp import FastMCP

app = FastMCP("ClipMate AI")

@app.tool()
def get_project_status():
    """Check the current ClipMate AI project status."""
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
    app.run()
