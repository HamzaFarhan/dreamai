# I want certain actions to loop until I'm satisfied with the result. But with a limit on the number of attempts.
expr = lambda x: x  # type: ignore
ASSISTANT = "assistant"
ACTION_ATTEMPTS_LIMIT = 3
[
    ("answer_question", "evaluate_answer"),
    # evaluate the answer and increment action_attempts if the evaluation is not satisfied and action_attempts is less than the limit
    (
        "evaluate_answer",
        ["increment_action_attempts", "answer_question"],
        ~expr("answer_evaluation.evaluation")
        & expr(f"action_attempts < {ACTION_ATTEMPTS_LIMIT}"),
    ),
    # if the evaluation is not satisfied and action_attempts is greater than or equal to the limit, reset action_attempts and go to the error_message action
    (
        "evaluate_answer",
        ["error_message", "reset_action_attempts"],
        ~expr("answer_evaluation.evaluation")
        & expr(f"action_attempts >= {ACTION_ATTEMPTS_LIMIT}"),
    ),
    # if the evaluation is satisfied, reset action_attempts and go to the final_message action
    (
        "evaluate_answer",
        ["final_message", "reset_action_attempts"],
        expr("answer_evaluation.evaluation"),
    ),
]  # type: ignore

# I can't go from evaluate_answer to increment_action_attempts and then from increment_action_attempts to the next action because increment_action_attempts would not know which action is being looped.

# For now I just increment or reset action_attempts at the end of evaluate_answer. But a standalone action would be better for reusability.
