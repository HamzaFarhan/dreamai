"""Google Sheets Structure MCP Server - Handles spreadsheet and sheet management"""
from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Import our API modules
from ..api.auth import GoogleSheetsAuth
from ..api.spreadsheet_ops import SpreadsheetOperations
from ..api.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

# Initialize MCP server and FastAPI app
mcp = FastMCP("Google Sheets Structure Server")
app = FastAPI(title="Google Sheets Structure MCP Server", version="1.0.0")

# Global auth and operations instances
auth = GoogleSheetsAuth(scope_level='full')
spreadsheet_ops = None

def get_spreadsheet_ops():
    """Get authenticated spreadsheet operations instance"""
    global spreadsheet_ops
    if spreadsheet_ops is None:
        service = auth.authenticate()
        spreadsheet_ops = SpreadsheetOperations(service)
    return spreadsheet_ops

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def create_spreadsheet(
    title: str,
    initial_sheets: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new Google Sheets spreadsheet.
    
    Args:
        title: The title for the new spreadsheet
        initial_sheets: Optional list of sheet names to create initially
        
    Returns:
        Dictionary containing spreadsheet_id, spreadsheet_url, and sheet names
    """
    try:
        ops = get_spreadsheet_ops()
        
        if initial_sheets:
            result = ops.create_with_sheets(title, initial_sheets)
        else:
            spreadsheet_id = ops.create(title)
            result = {
                'spreadsheet_id': spreadsheet_id,
                'spreadsheet_url': f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit',
                'sheets': ['Sheet1']  # Default sheet
            }
        
        logger.info(f"Created spreadsheet '{title}' with ID: {result['spreadsheet_id']}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create spreadsheet '{title}': {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def get_spreadsheet_info(spreadsheet_id: str) -> Dict[str, Any]:
    """
    Get metadata about a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        
    Returns:
        Dictionary containing spreadsheet metadata
    """
    try:
        ops = get_spreadsheet_ops()
        metadata = ops.get_metadata(spreadsheet_id)
        
        # Extract useful information
        result = {
            'spreadsheet_id': metadata['spreadsheetId'],
            'title': metadata['properties']['title'],
            'sheets': [
                {
                    'sheet_id': sheet['properties']['sheetId'],
                    'title': sheet['properties']['title'],
                    'grid_properties': sheet['properties'].get('gridProperties', {})
                }
                for sheet in metadata['sheets']
            ],
            'spreadsheet_url': metadata['spreadsheetUrl']
        }
        
        logger.info(f"Retrieved info for spreadsheet: {result['title']}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get spreadsheet info for ID '{spreadsheet_id}': {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def add_sheet(
    spreadsheet_id: str,
    sheet_name: str,
    rows: int = 1000,
    columns: int = 26
) -> Dict[str, Any]:
    """
    Add a new sheet to an existing spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: Name for the new sheet
        rows: Number of rows for the new sheet (default: 1000)
        columns: Number of columns for the new sheet (default: 26)
        
    Returns:
        Dictionary containing new sheet properties
    """
    try:
        ops = get_spreadsheet_ops()
        sheet_properties = ops.add_sheet(spreadsheet_id, sheet_name, rows, columns)
        
        result = {
            'sheet_id': sheet_properties['sheetId'],
            'title': sheet_properties['title'],
            'grid_properties': sheet_properties.get('gridProperties', {}),
            'success': True
        }
        
        logger.info(f"Added sheet '{sheet_name}' to spreadsheet {spreadsheet_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add sheet '{sheet_name}' to {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def delete_sheet(spreadsheet_id: str, sheet_id: int) -> Dict[str, Any]:
    """
    Delete a sheet from a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet to delete
        
    Returns:
        Dictionary indicating success/failure
    """
    try:
        ops = get_spreadsheet_ops()
        success = ops.delete_sheet(spreadsheet_id, sheet_id)
        
        result = {"success": success}
        if success:
            logger.info(f"Deleted sheet {sheet_id} from spreadsheet {spreadsheet_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete sheet {sheet_id} from {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def duplicate_sheet(
    spreadsheet_id: str,
    source_sheet_id: int,
    new_sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Duplicate an existing sheet in a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        source_sheet_id: The ID of the sheet to duplicate
        new_sheet_name: Optional name for the duplicated sheet
        
    Returns:
        Dictionary containing new sheet properties
    """
    try:
        ops = get_spreadsheet_ops()
        sheet_properties = ops.duplicate_sheet(spreadsheet_id, source_sheet_id, new_sheet_name)
        
        result = {
            'sheet_id': sheet_properties['sheetId'],
            'title': sheet_properties['title'],
            'grid_properties': sheet_properties.get('gridProperties', {}),
            'success': True
        }
        
        logger.info(f"Duplicated sheet {source_sheet_id} as '{sheet_properties['title']}' in {spreadsheet_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to duplicate sheet {source_sheet_id} in {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def update_sheet_properties(
    spreadsheet_id: str,
    sheet_id: int,
    title: Optional[str] = None,
    row_count: Optional[int] = None,
    column_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update properties of a sheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: The ID of the sheet to update
        title: New title for the sheet (optional)
        row_count: New row count (optional)
        column_count: New column count (optional)
        
    Returns:
        Dictionary indicating success/failure
    """
    try:
        ops = get_spreadsheet_ops()
        
        # Build grid properties if row/column counts are specified
        grid_properties = {}
        if row_count is not None:
            grid_properties['rowCount'] = row_count
        if column_count is not None:
            grid_properties['columnCount'] = column_count
        
        success = ops.update_sheet_properties(
            spreadsheet_id, 
            sheet_id, 
            title=title,
            grid_properties=grid_properties if grid_properties else None
        )
        
        result = {"success": success}
        if success:
            updates = []
            if title:
                updates.append(f"title to '{title}'")
            if row_count:
                updates.append(f"row count to {row_count}")
            if column_count:
                updates.append(f"column count to {column_count}")
            
            logger.info(f"Updated sheet {sheet_id} in {spreadsheet_id}: {', '.join(updates)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update sheet {sheet_id} in {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
async def get_auth_status() -> Dict[str, Any]:
    """
    Get the current authentication status and information.
    
    Returns:
        Dictionary containing authentication details
    """
    try:
        auth_info = auth.get_auth_info()
        return {
            "status": "success",
            "auth_info": auth_info
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "auth_info": {"authenticated": False}
        }

# ================== FASTAPI ENDPOINTS ==================

class MCPRequest(BaseModel):
    """Request model for MCP operations."""
    method: str = Field(..., description="MCP method to call")
    params: Dict[str, Any] = Field(default={}, description="Parameters for the method")

@app.post("/")
async def handle_mcp_request(request: MCPRequest) -> Dict[str, Any]:
    """
    Handle MCP requests via FastAPI endpoint.
    
    This endpoint processes MCP tool calls and returns appropriate responses.
    """
    try:
        if request.method == "tools/list":
            # Return list of available tools
            tools = []
            for tool_name, tool_func in mcp._tools.items():
                tool_info = {
                    "name": tool_name,
                    "description": tool_func.__doc__ or f"Tool: {tool_name}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                tools.append(tool_info)
            
            return {"tools": tools}
            
        elif request.method == "tools/call":
            # Call a specific tool
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if tool_name not in mcp._tools:
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
            # Call the tool
            result = await mcp._tools[tool_name](**arguments)
            
            # Format response according to MCP protocol
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ]
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {request.method}")
            
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Google Sheets Structure MCP Server"}

# Main function to run the server
def main():
    """Run the FastAPI server."""
    import sys
    
    # Add json import
    global json
    import json
    
    port = 3010  # Default port for structure server
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default port {port}")
    
    logger.info(f"Starting Google Sheets Structure MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

# Export the mcp instance for use by other modules
__all__ = ['mcp', 'app']