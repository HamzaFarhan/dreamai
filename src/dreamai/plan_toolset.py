from pydantic_ai import ModelRetry, RunContext

from .agent_deps import AgentDeps, Mode


async def create_plan_steps(ctx: RunContext[AgentDeps], plan: str) -> str:
    """
    Creates a new sequential markdown plan with systematic steps and presents it to the user.
    These steps are the atomic, unambiguous, sequential steps that you will follow to complete the task.

    Args:
        plan: The sequential steps formatted as markdown.

    Example:
        create_plan_steps(plan="## SEQUENTIAL STEPS\n1. Data preparation: Filter active customers using subscription table\n2. Base calculation: Calculate monthly revenue per customer cohort\n3. Final output: Generate cohort analysis table with retention metrics")
    """
    ctx.deps.mode = Mode.PLAN
    ctx.deps.update_plan(plan)
    return f"<sequential_plan>\n{plan}\n</sequential_plan>"


async def update_plan_steps(ctx: RunContext[AgentDeps], old_text: str, new_text: str) -> str:
    """
    Updates existing content in the plan.

    This function is typically used to **mark plan steps as completed** or to tweak their wording. It
    replaces all occurrences of `old_text` in the plan.

    **TOKEN-EFFICIENT BUT FEWER CALLS:**
    • Prefer bundling several related step updates in one call whenever a single action finishes multiple
    sequential steps. Reducing tool invocations is usually worth the few extra tokens a longer replacement string
    might consume.

    **Practical rules:**
    1. *Bulk completions* - If the steps are adjacent in the plan, select the contiguous block and
       append "COMPLETED ✓" to each line in a single replacement.
    2. *Sparse completions* - If the affected steps are far apart you may need multiple calls, but
       try grouping when reasonable.
    3. *Single-step edits* - For isolated tweaks, stick with the classic substring pattern.

    Args:
        old_text: String to locate the text to replace.
        new_text: The full replacement string.

    Examples
    --------
    Bulk completion of three contiguous steps:

        update_plan_steps(
            "Load customer data\n2. Transform customer data\n3. Validate customer data",
            "Load customer data - COMPLETED ✓\n2. Transform customer data - COMPLETED ✓\n3. Validate customer data - COMPLETED ✓",
        )

    Two similar revenue steps in one go:

        update_plan_steps(
            "Calculate revenue Q1 2023\nCalculate revenue Q2 2023",
            "Calculate revenue Q1 2023 - COMPLETED ✓\nCalculate revenue Q2 2023 - COMPLETED ✓",
        )

    Minimal single-step update:

        update_plan_steps("customer data", "customer data - COMPLETED ✓")
    """

    current_plan = ctx.deps.plan

    if current_plan is None:
        return "<sequential_plan>\nNo plan exists yet.\n</sequential_plan>"

    if old_text not in current_plan:
        raise ModelRetry(
            f"<sequential_plan>\nText not found in plan: '{old_text}'\n\nCurrent plan:\n{current_plan}\n</sequential_plan>"
        )
    ctx.deps.update_plan(current_plan.replace(old_text, new_text).strip())
    return f"<sequential_plan>\nUpdated plan step successfully.\n\n{ctx.deps.plan}\n</sequential_plan>"


async def add_plan_step(ctx: RunContext[AgentDeps], new_step: str) -> str:
    """
    Adds a new step to the sequential plan.

    This adds a new step to the end of the existing plan. Use this when you discover during analysis execution
    that additional steps are needed that weren't in the original user-approved plan, or when expanding the
    analysis scope based on findings.

    Args:
        new_step: The new step to add to the plan. Should be properly formatted and follow the atomic, sequential pattern (e.g., "6. Validate results against business logic").

    Example:
        add_plan_step("4. Validation step: Cross-check MRR calculations against transaction totals")
    """
    current_plan = ctx.deps.plan or ""
    ctx.deps.update_plan((current_plan.rstrip() + "\n" + new_step).strip())
    return f"<sequential_plan>\nAdded new step successfully.\n\n{ctx.deps.plan}\n</sequential_plan>"


async def load_plan_steps(ctx: RunContext[AgentDeps]) -> str:
    """
    Loads the current sequential plan.

    Use this to check the current plan status, see what steps have been completed, or reference the overall
    analysis approach.
    """
    return (
        f"<sequential_plan>\n"
        f"{ctx.deps.plan or 'No plan exists yet. Use create_plan_steps to create one.'}\n"
        f"</sequential_plan>"
    )


async def execute_plan_steps(ctx: RunContext[AgentDeps]):
    """Use this as soon as the user approves the plan to kickoff the execution."""
    ctx.deps.mode = Mode.ACT
