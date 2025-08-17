"""Google Sheets Chart MCP Server - Handles chart creation and management"""
from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import json

# Import our API modules
from ..api.auth import GoogleSheetsAuth
from ..api.batch_ops import BatchOperations
from ..api.range_resolver import RangeResolver
from ..api.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

# Initialize MCP server and FastAPI app
mcp = FastMCP("Google Sheets Chart Server")
app = FastAPI(title="Google Sheets Chart MCP Server", version="1.0.0")

# Global auth and operations instances
auth = GoogleSheetsAuth(scope_level='full')
batch_ops = None

def get_batch_ops():
    """Get authenticated batch operations instance"""
    global batch_ops
    if batch_ops is None:
        service = auth.authenticate()
        batch_ops = BatchOperations(service)
    return batch_ops

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def create_chart(
    spreadsheet_id: str,
    sheet_id: int,
    chart_type: str,
    data_range: str,
    title: str,
    position: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Create a chart in the spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_id: ID of the sheet where to place the chart
        chart_type: Type of chart ('LINE', 'COLUMN', 'PIE', etc.)
        data_range: Range containing chart data in A1 notation
        title: Title for the chart
        position: Optional position {'row': int, 'col': int}
        
    Returns:
        Dictionary containing chart creation result
    """
    try:
        parsed_range = RangeResolver.parse_a1_notation(data_range)
        
        chart_spec = {
            "title": title,
            "basicChart": {
                "chartType": chart_type.upper(),
                "domains": [{
                    "domain": {
                        "sourceRange": {
                            "sources": [{
                                "sheetId": sheet_id,
                                "startRowIndex": parsed_range.start_row,
                                "endRowIndex": parsed_range.end_row + 1 if parsed_range.end_row is not None else parsed_range.start_row + 1,
                                "startColumnIndex": parsed_range.start_col,
                                "endColumnIndex": parsed_range.start_col + 1
                            }]
                        }
                    }
                }],
                "series": [{
                    "series": {
                        "sourceRange": {
                            "sources": [{
                                "sheetId": sheet_id,
                                "startRowIndex": parsed_range.start_row,
                                "endRowIndex": parsed_range.end_row + 1 if parsed_range.end_row is not None else parsed_range.start_row + 1,
                                "startColumnIndex": parsed_range.start_col + 1,
                                "endColumnIndex": parsed_range.end_col + 1 if parsed_range.end_col is not None else parsed_range.start_col + 2
                            }]
                        }
                    }
                }]
            }
        }
        
        # Set position if provided
        embedded_object_position = {
            "sheetId": sheet_id,
            "overlayPosition": {
                "anchorCell": {
                    "sheetId": sheet_id,
                    "rowIndex": position.get('row', 0) if position else 0,
                    "columnIndex": position.get('col', 5) if position else 5
                }
            }
        }
        
        request = {
            "addChart": {
                "chart": {
                    "spec": chart_spec,
                    "position": embedded_object_position
                }
            }
        }
        
        ops = get_batch_ops()
        result = ops.batch_update(spreadsheet_id, [request])
        
        response = {
            'chart_type': chart_type,
            'data_range': data_range,
            'title': title,
            'sheet_id': sheet_id,
            'success': True
        }
        
        logger.info(f"Created {chart_type} chart in {spreadsheet_id} sheet {sheet_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create chart in {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
@ErrorHandler.retry_with_backoff(max_retries=3)
async def create_pivot_table(
    spreadsheet_id: str,
    source_sheet_id: int,
    target_sheet_id: int,
    data_range: str,
    rows: List[str],
    columns: List[str],
    values: List[str]
) -> Dict[str, Any]:
    """
    Create a pivot table.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        source_sheet_id: ID of the sheet containing source data
        target_sheet_id: ID of the sheet where to place pivot table
        data_range: Range containing pivot data in A1 notation
        rows: List of column names for row grouping
        columns: List of column names for column grouping  
        values: List of column names for value aggregation
        
    Returns:
        Dictionary containing pivot table creation result
    """
    try:
        parsed_range = RangeResolver.parse_a1_notation(data_range)
        
        pivot_table = {
            "source": {
                "sheetId": source_sheet_id,
                "startRowIndex": parsed_range.start_row,
                "endRowIndex": parsed_range.end_row + 1 if parsed_range.end_row is not None else parsed_range.start_row + 1000,
                "startColumnIndex": parsed_range.start_col,
                "endColumnIndex": parsed_range.end_col + 1 if parsed_range.end_col is not None else parsed_range.start_col + 10
            },
            "rows": [{"sourceColumnOffset": i, "showTotals": True} for i, _ in enumerate(rows)],
            "columns": [{"sourceColumnOffset": i + len(rows), "showTotals": True} for i, _ in enumerate(columns)],
            "values": [{
                "sourceColumnOffset": i + len(rows) + len(columns),
                "summarizeFunction": "SUM"
            } for i, _ in enumerate(values)]
        }
        
        request = {
            "addPivotTable": {
                "pivotTable": pivot_table,
                "anchorCell": {
                    "sheetId": target_sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0
                }
            }
        }
        
        ops = get_batch_ops()
        result = ops.batch_update(spreadsheet_id, [request])
        
        response = {
            'data_range': data_range,
            'rows': rows,
            'columns': columns,
            'values': values,
            'success': True
        }
        
        logger.info(f"Created pivot table in {spreadsheet_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create pivot table in {spreadsheet_id}: {e}")
        return {"error": str(e), "success": False}

@mcp.tool()
async def get_chart_types() -> Dict[str, Any]:
    """
    Get available chart types and their descriptions.
    
    Returns:
        Dictionary of available chart types
    """
    chart_types = {
        'LINE': 'Line chart for showing trends over time',
        'COLUMN': 'Column chart for comparing values',
        'BAR': 'Bar chart for horizontal comparisons',
        'PIE': 'Pie chart for showing parts of a whole',
        'SCATTER': 'Scatter plot for showing correlation',
        'AREA': 'Area chart for showing cumulative values',
        'HISTOGRAM': 'Histogram for showing distribution',
        'CANDLESTICK': 'Candlestick chart for financial data'
    }
    
    return {
        'chart_types': chart_types,
        'total_types': len(chart_types),
        'success': True
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
    return {"status": "healthy", "service": "Google Sheets Chart MCP Server"}

# Main function to run the server
def main():
    """Run the FastAPI server."""
    import sys
    
    port = 3014  # Default port for chart server
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default port {port}")
    
    logger.info(f"Starting Google Sheets Chart MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

# Export the mcp instance and app
__all__ = ['mcp', 'app']