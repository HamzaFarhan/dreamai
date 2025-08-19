# Finn AI Agent - Gradio UI

A comprehensive web interface for the Finn AI Agent, providing an intuitive way to interact with your data analysis assistant.

## Features

### 🎯 Project Management
- **Create Projects**: Start new analysis projects with custom names
- **Switch Projects**: Seamlessly switch between different projects
- **Project Isolation**: Each project maintains its own chat history, plans, and results

### 📊 Data Management
- **File Upload**: Upload CSV and Parquet files for analysis
- **Shared Data**: Data files are shared across all projects in a workspace
- **File Browser**: View and select available data files

### 💬 Interactive Chat
- **AI Conversations**: Chat with Finn about your data and analysis needs
- **Message History**: Persistent chat history for each project
- **Real-time Responses**: Get immediate feedback from the AI agent

### 📋 Live Plan Tracking
- **Dynamic Plans**: View the AI's step-by-step analysis plan
- **Live Updates**: Plan updates in real-time as the agent works
- **Progress Tracking**: See which steps are completed and which are pending

### 📈 Workbook Preview
- **Excel Preview**: View generated Excel files directly in the browser
- **Live Updates**: Workbook updates automatically when new files are created
- **Download**: Download Excel files for use in external applications

### 🎨 User Interface
- **Clean Design**: White theme with light grey gradients
- **Responsive Layout**: Three-panel layout that adapts to screen size
- **Visual Indicators**: Orange dots show when tabs have been updated
- **Collapsible Panels**: Maximize space for the chat interface

## Installation

1. **Install Dependencies**:
   ```bash
   uv add gradio pandas openpyxl
   ```

2. **Set up Environment**:
   Make sure you have your AI model API keys configured in your environment.

## Usage

### Quick Start

1. **Launch the UI**:
   ```bash
   python finn/test_ui.py
   ```

2. **Open Browser**:
   Navigate to `http://localhost:7860`

3. **Create a Project**:
   - Enter a project name in the "New Project" section
   - Click "Create Project"

4. **Upload Data**:
   - Use the file upload in the "Data Files" section
   - Upload CSV or Parquet files

5. **Start Chatting**:
   - Type your analysis request in the message box
   - Watch the plan update in real-time
   - Download results from the workbook tab

### Advanced Usage

#### Custom Workspace
```python
from finn.gradio_ui import launch_finn_ui
from pathlib import Path

# Launch with custom workspace
launch_finn_ui(
    workspace_dir=Path("/path/to/your/workspace"),
    server_port=8080,
    share=True  # Enable public sharing
)
```

#### Integration with Existing Code
```python
from finn.gradio_ui import FinnUI
from pathlib import Path

# Create UI instance
ui = FinnUI(workspace_dir=Path("my_workspace"))

# Get the Gradio interface
demo = ui.create_interface()

# Launch with custom settings
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    auth=("username", "password")  # Add authentication
)
```

## File Structure

```
workspace/
├── data/                    # Shared data files (CSV, Parquet)
└── threads/                 # Project-specific directories
    ├── project1/
    │   ├── chat_message_history.json
    │   ├── plan.md
    │   └── results/         # Generated Excel files
    └── project2/
        ├── chat_message_history.json
        ├── plan.md
        └── results/
```

## Configuration

### Environment Variables
- Set your AI model API keys as environment variables
- Configure model settings in your `.env` file

### Workspace Settings
- **Default Workspace**: `workspaces/session`
- **Data Directory**: `workspace/data` (shared across projects)
- **Results Directory**: `workspace/threads/{project}/results`

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Make sure you're in the correct directory
   cd /path/to/dreamai
   python -m finn.test_ui
   ```

2. **Port Already in Use**:
   ```python
   # Use a different port
   launch_finn_ui(server_port=8080)
   ```

3. **File Upload Issues**:
   - Ensure files are CSV or Parquet format
   - Check file permissions
   - Verify workspace directory is writable

4. **Agent Not Responding**:
   - Check API key configuration
   - Verify network connectivity
   - Check console for error messages

### Performance Tips

- **Large Files**: For large datasets, consider using Parquet format
- **Memory Usage**: Monitor memory usage with many concurrent users
- **Network**: Use `share=False` for local-only access

## Development

### Adding New Features

1. **Extend FinnUI Class**:
   ```python
   class CustomFinnUI(FinnUI):
       def custom_feature(self):
           # Add your feature here
           pass
   ```

2. **Add Event Handlers**:
   ```python
   # In create_interface method
   new_component.click(
       your_handler_function,
       inputs=[input_components],
       outputs=[output_components]
   )
   ```

3. **Customize Theme**:
   ```python
   custom_theme = gr.themes.Default().set(
       primary_hue="green",
       button_primary_background_fill="#00AA00"
   )
   ```

## API Reference

### FinnUI Class

#### Methods
- `__init__(workspace_dir)`: Initialize UI with workspace
- `create_interface()`: Create Gradio interface
- `_create_agent_deps(project_name)`: Create agent dependencies
- `_get_projects_list()`: Get list of available projects
- `_get_data_files()`: Get list of data files
- `_load_chat_history(project_name)`: Load chat history
- `_save_chat_history(project_name, history)`: Save chat history

#### Properties
- `workspace_dir`: Path to workspace directory
- `current_project`: Currently active project name
- `current_agent_deps`: Current agent dependencies

### Launch Function

```python
launch_finn_ui(
    workspace_dir: Path = Path("workspaces/session"),
    **kwargs  # Additional Gradio launch parameters
) -> tuple[App, str, str]
```

## License

This project is part of the DreamAI framework. See the main project license for details.
