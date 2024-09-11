# Dialog Engineering: A Comprehensive Guide

## Introduction

Dialog Engineering is an innovative approach to prompt engineering that leverages conversational context to create more effective AI interactions. This guide explains the key concepts, components, and usage of Dialog Engineering as implemented in our project.

## Key Concepts

1. **Task as System Prompt**: The system prompt is defined as the "task", which can be a string or loaded from a separate text file (e.g., `answer_eval_task.txt`). It sets the AI's role and objectives.

2. **Examples as Dialog History**: Uses a series of user-AI interactions as examples, simulating real conversations to guide the AI's behavior.

3. **Good and Bad Examples**: 
   - **GoodExample**: A user message followed by an appropriate assistant message, showcasing a successful interaction.
   - **BadExample**: A user message, an inadequate assistant message, and another user message providing feedback to guide improvement.

4. **Dialog Object**: Encapsulates the entire prompt, including the task, template, and examples. Typically stored as a JSON file.

5. **Message Template**: Ensures consistency in the format of user messages across examples and actual interactions.

## Implementation Details

### Dialog Class (from `src/dreamai/dialog.py`)

The `Dialog` class handles the creation, manipulation, and storage of dialogs. Key attributes include:

- `task`: The system prompt defining the AI's role and objectives.
- `template`: The user message template for consistent formatting.
- `examples`: A list of `Example` or `BadExample` instances representing simulated user-AI interactions.
- `chat_history`: The actual conversation history between the user and AI.
- `version`: The current version of the dialog for tracking changes.

### Creating a Dialog

To create a new dialog:

1. Define the task (system prompt) as a string or in a separate text file, such as `answer_eval_task.txt`:

```src/dreamai/dialogs/answer_eval_task.txt
You are a world-class AI evaluator with unparalleled expertise in natural language understanding, query-answer relevance assessment, and factual accuracy. Your task is to determine whether a given answer truly addresses the user's query, is correct, and, if applicable, is grounded in the provided source documents.

Given:
1. The user's original query
2. The generated answer to that query
3. The source documents used to generate the answer (if provided)

Your task is to analyze the query, the answer, and the source documents (if available), then provide a boolean response indicating whether the answer adequately addresses the user's query, is correct, and, when applicable, is based on the source documents. Include a short explanation of your reasoning.

Instructions:
1. Carefully examine the user's query to understand the main question, intent, and any specific requirements.
2. If the query is a simple greeting (e.g., "Hello", "Hi") or farewell (e.g., "Goodbye", "Thanks"), treat the evaluation more leniently. A polite and appropriate response should be considered correct in these cases.
3. For all other queries, analyze the generated answer in relation to the query.
4. If source documents are provided:
   a. Review them to understand what information was available to generate the answer.
   b. Ensure that the answer is grounded in and consistent with the information provided by the source documents.
   c. Check that the answer does not contain significant information that is not present in the source documents.
   d. Consider the answer correct if it aligns with the information in the source documents, regardless of your own knowledge.
5. If source documents are not provided:
   a. Evaluate whether the answer directly addresses the core aspects of the user's query.
   b. Assess the factual correctness of the answer based on your own knowledge and expertise.
6. Provide a short, clear explanation of your reasoning for the evaluation.
7. When source documents are provided, do NOT question their correctness, even if you believe they may be outdated or inaccurate. Treat all information in the source documents as factual and up-to-date.

Evaluation Criteria:
- Return True if:
  a. The answer directly addresses the main point(s) of the user's query.
  b. The answer is factually correct (based on source documents if provided, or your own knowledge if not).
  c. When source documents are provided, the information in the answer is clearly derived from and consistent with them.
  d. The answer fulfills any specific requirements mentioned in the query.

- Return False if:
  a. The answer is off-topic or addresses a different question than what was asked.
  b. The answer is factually incorrect (based on source documents if provided, or your own knowledge if not).
  c. When source documents are provided, the answer contains significant information that is not present in them or contradicts them.
  d. The answer is too vague or general to be considered a real attempt at addressing the specific query.
  e. The answer ignores key aspects or requirements of the query.

Output:
Provide a JSON object with the following structure:
{
  "evaluation": boolean,
  "reasoning": "A short sentence explaining your evaluation"
}

The boolean value should be:
- true if the answer addresses the query, is correct, and (when applicable) is grounded in the source documents
- false if the answer does not address the query, is incorrect, or (when applicable) is not based on the source documents

Your task is to make a judgment based on query-answer relevance, factual correctness, and, when applicable, the answer's grounding in the source documents. Ensure your reasoning reflects this focus. Remember, when source documents are provided, do not question or comment on their accuracy or currency - treat them as absolute truth for this evaluation, even if they contradict your own knowledge.
```

2. Create a JSON file with the following structure:

```json:src/dreamai/dialogs/answer_eval_dialog.json
{
  "task": "answer_eval_task.txt",
  "template": "<user_query>{query}</user_query>\n\n<source_docs>{source_docs}</source_docs>\n\n<generated_answer>{answer}</generated_answer>",
  "examples": [
    {
      "user": "<user_query>What is the capital of France?</user_query>...",
      "assistant": "Paris is the capital of France..."
    },
    {
      "user": "<user_query>How does photosynthesis work?</user_query>...",
      "assistant": "Photosynthesis is the process by which plants convert sunlight into energy...",
      "feedback": "The answer doesn't provide enough detail about the specific steps involved in photosynthesis."
    }
  ]
}
```

3. Load the JSON file using the `Dialog.load()` method:

```python
dialog = Dialog.load(path="src/dreamai/dialogs/answer_eval_dialog.json")
```

### Using a Dialog

To use a dialog for an AI interaction:

1. Create a `Dialog` instance by loading the JSON file:

```python
dialog = Dialog.load(path="src/dreamai/dialogs/answer_eval_dialog.json")
```

2. Add the user's input to the dialog using the `add_user_message()` method:

```python
dialog.add_user_message(content="What is the capital of France?")
```

3. Generate the AI's response using the `creator_with_kwargs()` method to prepare the appropriate arguments for the selected AI model (e.g., GPT, Claude, Gemini):

```python
creator, creator_kwargs = dialog.creator_with_kwargs(
    model=ModelName.GPT, user="What is the capital of France?"
)
response = creator.create(**creator_kwargs)
```

4. Add the AI's response to the dialog using the `add_assistant_message()` method:

```python
dialog.add_assistant_message(content=response)
```

5. Repeat steps 2-4 for each user-AI interaction in the conversation.

### Updating a Dialog

To update a dialog's task, template, or version:

1. Use the `update()` method of the `Dialog` class, providing the new task, template, and/or version:

```python
dialog.update(
    new_task="updated_task.txt",
    new_template="<user_query>{query}</user_query>\n\n<context>{context}</context>",
    new_version=2.0,
)
```

2. The method will automatically generate a diff of the changes and update the dialog's attributes.

3. Save the updated dialog using the `save()` method:

```python
dialog.save(name="updated_answer_eval_dialog")
```

## Benefits of Dialog Engineering

1. **Context-awareness**: The dialog structure provides context for each interaction, enabling the AI to generate more relevant and coherent responses.

2. **Quality control**: The inclusion of both good and bad examples helps the AI understand the expected response quality and adapt accordingly.

3. **Consistency**: The template ensures that user inputs are formatted consistently, making it easier for the AI to process and respond to them.

4. **Flexibility**: The dialog engineering approach can be applied to various tasks and domains, allowing for customization based on specific requirements.

## Conclusion

Dialog Engineering offers a powerful and flexible approach to designing effective AI interactions. By structuring prompts as conversations and leveraging context, it enables the creation of more engaging, coherent, and high-quality AI responses. The `Dialog` class in our project provides a convenient way to create, manipulate, and use dialogs for various AI-powered applications.