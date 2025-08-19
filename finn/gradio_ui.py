from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import pandas as pd

from .finn_deps import DataDirs, FinnDeps
from .toolset_agent import (
    excel_charts_toolset,
    excel_formatting_toolset,
    excel_formula_toolset,
    excel_structure_toolset,
    run_agent,
)


class FinnUI:
    def __init__(self, workspace_dir: Path = Path("workspaces/session")):
        self.workspace_dir = workspace_dir.expanduser().resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize with default project
        self.current_project = self._load_last_project()
        self.current_agent_deps = self._create_agent_deps(self.current_project)

    def _load_last_project(self) -> str:
        """Load the last selected project from persistence"""
        settings_file = self.workspace_dir / "settings.json"
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text())
                last_project = settings.get("last_project", "default")
                # Verify the project still exists
                if last_project in self._get_projects_list():
                    return last_project
            except Exception:
                pass
        return "default"

    def _save_last_project(self, project_name: str):
        """Save the current project as the last selected"""
        settings_file = self.workspace_dir / "settings.json"
        settings = {}
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text())
            except Exception:
                pass
        settings["last_project"] = project_name
        settings_file.write_text(json.dumps(settings, indent=2))

    def _create_agent_deps(self, project_name: str) -> FinnDeps:
        """Create AgentDeps for a given project"""
        thread_dir = self.workspace_dir / f"threads/{project_name}"
        return FinnDeps(
            dirs=DataDirs(workspace_dir=self.workspace_dir, thread_dir=thread_dir),
            toolsets={
                "excel_structure_toolset": excel_structure_toolset,
                "excel_formula_toolset": excel_formula_toolset,
                "excel_charts_toolset": excel_charts_toolset,
                "excel_formatting_toolset": excel_formatting_toolset,
            },
            plan_path=thread_dir / "plan.md",
        )

    def _get_projects_list(self) -> list[str]:
        """Get list of existing projects"""
        threads_dir = self.workspace_dir / "threads"
        if not threads_dir.exists():
            return ["default"]
        return [d.name for d in threads_dir.iterdir() if d.is_dir()]

    def _get_data_files(self) -> list[str]:
        """Get list of data files"""
        data_dir = self.workspace_dir / "data"
        if not data_dir.exists():
            return []
        files: list[str] = []
        for file in data_dir.iterdir():
            if file.suffix.lower() in [".csv", ".parquet"]:
                files.append(str(file.name))
        return files

    def _format_data_files_html(self) -> str:
        """Format data files as HTML list"""
        files = self._get_data_files()
        if not files:
            return "<p style='color: #666; font-style: italic;'>No data files available</p>"
        
        file_items = "".join([f"<li style='padding: 2px 0;'>{file}</li>" for file in files])
        return f"""
        <div style='max-height: 35vh; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px;'>
            <ul style='margin: 0; padding-left: 20px;'>
                {file_items}
            </ul>
        </div>
        """

    def _load_chat_history(self, project_name: str) -> list[dict[str, str]]:
        """Load chat history for a project"""
        chat_file = self.workspace_dir / f"threads/{project_name}/chat_message_history.json"
        if chat_file.exists():
            try:
                return json.loads(chat_file.read_text())
            except Exception:
                return []
        return []

    def _save_chat_history(self, project_name: str, history: list[dict[str, str]]):
        """Save chat history for a project"""
        chat_file = self.workspace_dir / f"threads/{project_name}/chat_message_history.json"
        chat_file.parent.mkdir(parents=True, exist_ok=True)
        chat_file.write_text(json.dumps(history, indent=2))

    def _get_latest_plan(self, project_name: str) -> str:
        """Get the latest plan content"""
        agent_deps = self._create_agent_deps(project_name)
        if agent_deps.plan_path.exists():
            return agent_deps.plan_path.read_text()
        return "No plan available yet."

    def _get_latest_workbook(self, project_name: str) -> tuple[pd.DataFrame | None, str | None]:
        """Get the latest Excel file as DataFrame and file path"""
        results_dir = self.workspace_dir / f"threads/{project_name}/results"
        if not results_dir.exists():
            return None, None

        xlsx_files = list(results_dir.glob("*.xlsx"))
        if not xlsx_files:
            return None, None

        # Get the most recent file
        latest_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
        try:
            df: pd.DataFrame = pd.read_excel(latest_file)
            return df, str(latest_file)
        except Exception:
            return None, str(latest_file)

    async def _process_message(self, message: str, project_name: str) -> tuple[str, list[dict[str, str]]]:
        """Process user message and return response with updated history"""
        if not message.strip():
            return "", self._load_chat_history(project_name)

        # Load current history
        history: list[dict[str, str]] = self._load_chat_history(project_name)

        # Add user message
        history.append({"user": message})

        # Get agent response
        agent_deps = self._create_agent_deps(project_name)
        try:
            response: str = await run_agent(message, agent_deps)
            history.append({"finn": response})
        except Exception as e:
            response = f"Error: {str(e)}"
            history.append({"finn": response})

        # Save updated history
        self._save_chat_history(project_name, history)

        return "", history

    def _format_chat_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        """Format chat history for Gradio Chatbot component"""
        formatted: list[dict[str, str]] = []
        for msg in history:
            if "user" in msg:
                formatted.append({"role": "user", "content": msg["user"]})
            elif "finn" in msg:
                formatted.append({"role": "assistant", "content": msg["finn"]})
        return formatted

    def create_interface(self):
        """Create the main Gradio interface"""

        with gr.Blocks(
            title="finn",
            theme=gr.themes.Default(primary_hue="gray", secondary_hue="gray", neutral_hue="gray").set(
                body_background_fill="white",
                block_background_fill="#f8f9fa",
                button_primary_background_fill="#6c757d",
                button_primary_text_color="white",
                body_text_color="black",
                block_title_text_color="black",
                block_label_text_color="black",
                input_background_fill="white",
                input_border_color="#dee2e6",
                border_color_primary="#dee2e6",
            ),
        ) as demo:
            # State variables
            current_project_state = gr.State(value=self.current_project)
            plan_last_modified = gr.State(value=0)
            workbook_last_modified = gr.State(value=0)

            # Header
            with gr.Row():
                gr.HTML("<h1 style='text-align: center; margin: 0;'>finn</h1>")

            with gr.Row():
                project_name_display = gr.HTML(
                    f"<h3 style='text-align: center; color: #666;'>Project: {self.current_project}</h3>"
                )

            # Main layout
            with gr.Row():
                # Left Panel - Projects & Data
                with gr.Column(scale=2, min_width=250):
                    with gr.Accordion("Projects & Data", open=True):
                        # New Project Section
                        with gr.Group():
                            gr.Markdown("### New Project")
                            new_project_name = gr.Textbox(
                                placeholder="Enter project name...", label="Project Name", scale=3
                            )
                            create_project_btn = gr.Button("Create Project", variant="primary")


                        # Previous Projects Section
                        with gr.Group():
                            gr.Markdown("### Previous Projects")
                            projects_list = gr.Dropdown(
                                choices=self._get_projects_list(),
                                label="Select Project",
                                value=self.current_project,
                            )

                        # Data Files Section
                        with gr.Group():
                            gr.Markdown("### Data Files")
                            upload_files = gr.File(
                                file_count="multiple",
                                file_types=[".csv", ".parquet"],
                                label="Upload CSV/Parquet Files",
                            )
                            data_files_list = gr.HTML(
                                value=self._format_data_files_html(),
                                label="Available Data Files",
                            
                            )

                # Center Panel - Chat
                with gr.Column(scale=4):
                    gr.Markdown("### Chat with Finn")

                    chatbot = gr.Chatbot(
                        value=[], 
                        show_label=False, 
                        type="messages",
                        height="70vh",
                        container=True,
                        autoscroll=True
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask Finn anything about your data...", label="Message", scale=4
                        )
                        send_btn = gr.Button("Send", variant="primary", scale=1)

                # Right Panel - Inquiry Details
                with gr.Column(scale=3, min_width=300):
                    with gr.Accordion("Inquiry Details", open=True):
                        with gr.Tabs() as inquiry_tabs:
                            # Plan Tab
                            with gr.Tab("Plan", id="plan_tab") as plan_tab:
                                plan_content = gr.Markdown(value="No plan available yet.", label="Current Plan")
                                plan_updated_indicator = gr.HTML("")

                            # Workbook Tab
                            with gr.Tab("Workbook", id="workbook_tab") as workbook_tab:
                                workbook_download = gr.File(label="Download Workbook", visible=False)
                                workbook_updated_indicator = gr.HTML("")

            # Timer for live updates
            update_timer = gr.Timer(value=2.0)  # Update every 2 seconds

            # Event handlers
            def create_new_project(project_name: str, current_project: str):
                """Create a new project and switch to it"""
                if not project_name.strip():
                    return current_project, current_project, gr.Dropdown(choices=self._get_projects_list())

                # Create new project
                new_project = project_name.strip()
                self.current_project = new_project
                self.current_agent_deps = self._create_agent_deps(new_project)
                self._save_last_project(new_project)

                # Update UI
                updated_projects = self._get_projects_list()
                return (
                    new_project,
                    new_project,
                    gr.Dropdown(choices=updated_projects, value=new_project),
                    gr.HTML(f"<h3 style='text-align: center; color: #666;'>Project: {new_project}</h3>"),
                    [],  # Clear chat
                    "",  # Clear input
                )

            def switch_project(selected_project: str, current_project: str):
                """Switch to a different project"""
                if selected_project == current_project:
                    return (
                        current_project,
                        [],
                        gr.HTML(f"<h3 style='text-align: center; color: #666;'>Project: {current_project}</h3>"),
                        gr.HTML(value=self._format_data_files_html()),  # Refresh data files list
                    )

                self.current_project = selected_project
                self.current_agent_deps = self._create_agent_deps(selected_project)
                self._save_last_project(selected_project)

                # Load chat history for the selected project
                history = self._load_chat_history(selected_project)
                formatted_history = self._format_chat_history(history)

                return (
                    selected_project,
                    formatted_history,
                    gr.HTML(f"<h3 style='text-align: center; color: #666;'>Project: {selected_project}</h3>"),
                    gr.HTML(value=self._format_data_files_html()),  # Refresh data files list
                )

            def handle_file_upload(files):
                """Handle uploaded data files"""
                if not files:
                    return gr.HTML(value=self._format_data_files_html())

                data_dir = self.workspace_dir / "data"
                data_dir.mkdir(parents=True, exist_ok=True)

                for file in files:
                    if hasattr(file, "name"):
                        # Copy file to data directory
                        file_path = Path(file.name)
                        dest_path = data_dir / file_path.name
                        dest_path.write_bytes(file_path.read_bytes())

                return gr.HTML(value=self._format_data_files_html())

            def send_message(message: str, history, current_project: str):
                """Handle sending a message to the agent"""
                if not message.strip():
                    return history, ""

                # Add user message to history immediately
                new_history = history + [{"role": "user", "content": message}]

                # Process message asynchronously
                def process_async():
                    import asyncio

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        _, full_history = loop.run_until_complete(self._process_message(message, current_project))
                        formatted = self._format_chat_history(full_history)
                        return formatted
                    finally:
                        loop.close()

                try:
                    result = process_async()
                    return result, ""
                except Exception as e:
                    # Update the last message with error
                    error_history = new_history + [{"role": "assistant", "content": f"Error: {str(e)}"}]
                    return error_history, ""

            def update_plan_content(current_project: str, last_modified: float):
                """Update plan content if file has been modified"""
                agent_deps = self._create_agent_deps(current_project)
                if not agent_deps.plan_path.exists():
                    return "No plan available yet.", last_modified, ""

                current_modified = agent_deps.plan_path.stat().st_mtime
                if current_modified > last_modified:
                    content = agent_deps.plan_path.read_text()
                    # Use CSS to make the Plan tab text yellow
                    indicator = '''
                    <style>
                    button[id*="plan_tab"] {
                        color: #fbbf24 !important;
                    }
                    </style>
                    '''
                    return content, current_modified, indicator

                return gr.skip(), last_modified, ""

            def update_workbook_content(current_project: str, last_modified: float):
                """Update workbook content if new file is available"""
                df, file_path = self._get_latest_workbook(current_project)

                if file_path is None:
                    return (
                        last_modified, 
                        "", 
                        gr.File(visible=False),
                    )

                current_modified = Path(file_path).stat().st_mtime
                if current_modified > last_modified:
                    # Use CSS to make the Workbook tab text yellow
                    indicator = '''
                    <style>
                    button[id*="workbook_tab"] {
                        color: #fbbf24 !important;
                    }
                    </style>
                    '''
                    
                  
                    
                    return (
                        current_modified, 
                        indicator, 
                        gr.File(value=file_path, visible=True),
                    )

                return (
                    gr.skip(), 
                    "", 
                    gr.skip()
                )

            # Bind event handlers
            create_project_btn.click(
                create_new_project,
                inputs=[new_project_name, current_project_state],
                outputs=[
                    current_project_state,
                    projects_list,
                    project_name_display,
                    chatbot,
                    new_project_name,
                ],
            )

            projects_list.change(
                switch_project,
                inputs=[projects_list, current_project_state],
                outputs=[current_project_state, chatbot, project_name_display, data_files_list],  # Add data_files_list to outputs
            )

            upload_files.upload(handle_file_upload, inputs=[upload_files], outputs=[data_files_list])

            # Chat functionality
            msg_input.submit(
                send_message, inputs=[msg_input, chatbot, current_project_state], outputs=[chatbot, msg_input]
            )

            send_btn.click(
                send_message, inputs=[msg_input, chatbot, current_project_state], outputs=[chatbot, msg_input]
            )

            # Live updates using timer
            update_timer.tick(
                update_plan_content,
                inputs=[current_project_state, plan_last_modified],
                outputs=[plan_content, plan_last_modified, plan_updated_indicator],
            )

            update_timer.tick(
                update_workbook_content,
                inputs=[current_project_state, workbook_last_modified],
                outputs=[workbook_last_modified, workbook_updated_indicator, workbook_download],
            )

        return demo


def launch_finn_ui(workspace_dir: Path = Path("workspaces/session"), **kwargs):
    """Launch the Finn UI"""
    ui = FinnUI(workspace_dir)
    demo = ui.create_interface()
    return demo.launch(**kwargs)


if __name__ == "__main__":
    launch_finn_ui(share=False, server_name="0.0.0.0", server_port=7860)
