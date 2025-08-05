plan_model = OpenAIModel("google/gemini-2.5-flash", provider=OpenRouterProvider())
act_model = OpenAIModel("openrouter/horizon-beta", provider=OpenRouterProvider())
agent = Agent(
    instructions=[plan_mode_instructions, step_instructions],
    deps_type=PlanAndActDeps,
    output_type=[
        ToolOutput(user_interaction, name="user_interaction"),
        ToolOutput(create_plan, name="create_plan"),
        ToolOutput(execute_plan, name="execute_plan"),
        ToolOutput(task_result, name="task_result"),
        ToolOutput(step_result, name="step_result"),
        ToolOutput(need_help, name="need_help"),
    ],
    prepare_output_tools=prepare_output_tools,
    retries=3,
)