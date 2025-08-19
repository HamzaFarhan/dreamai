#!/usr/bin/env python3
"""
Test script for the Finn Gradio UI
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import finn
sys.path.insert(0, str(Path(__file__).parent.parent))

from finn.gradio_ui import launch_finn_ui

if __name__ == "__main__":
    # Create a test workspace
    test_workspace = Path("test_workspace")
    test_workspace.mkdir(exist_ok=True)

    print("🚀 Launching Finn UI...")
    print("📁 Workspace:", test_workspace.absolute())
    print("🌐 URL: http://localhost:7860")
    print("\n✨ Features available:")
    print("  • Create and switch between projects")
    print("  • Upload CSV/Parquet data files")
    print("  • Chat with Finn AI agent")
    print("  • Live-updating plan view")
    print("  • Live-updating workbook preview")
    print("  • Download generated Excel files")

    try:
        launch_finn_ui(
            workspace_dir=test_workspace, share=False, server_name="0.0.0.0", server_port=7860, show_error=True
        )
    except KeyboardInterrupt:
        print("\n👋 Finn UI stopped.")
    except Exception as e:
        print(f"\n❌ Error launching UI: {e}")
        print("\n🔧 Make sure you have all dependencies installed:")
        print("  uv add gradio pandas")
