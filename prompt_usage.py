# Prompt Usage Tutorial: Finance Use Case

# First, let's import the necessary modules
from dreamai.prompt import Prompt, Example, BadExample
from dreamai.ai import user_message, assistant_message
from pathlib import Path
import json

# Markdown: Introduction
print("""
# Using the Prompt Class for Financial Analysis

This tutorial demonstrates how to use the `Prompt` class from the `dreamai.prompt` module for financial analysis tasks. We'll walk through various features of the `Prompt` class using a finance-related example.

## 1. Creating a Basic Prompt

Let's start by creating a simple prompt for a financial advisor chatbot:
""")

# Create a basic prompt
financial_advisor_prompt = Prompt(
    system="You are an AI financial advisor. Provide clear, concise, and accurate financial advice based on the user's questions.",
    description="Basic financial advisor chatbot"
)

print("Basic Prompt created:")
print(json.dumps(financial_advisor_prompt.model_dump(), indent=2))

# Markdown: Adding Examples
print("""
## 2. Adding Examples

We can improve our prompt by adding examples of good interactions:
""")

# Add examples
financial_advisor_prompt.examples.extend([
    Example(
        user="What's the difference between stocks and bonds?",
        assistant="Stocks represent ownership in a company, while bonds are loans to a company or government. Stocks generally offer higher potential returns but with higher risk, whereas bonds typically provide more stable, lower returns with less risk."
    ),
    Example(
        user="How should I start investing with a small budget?",
        assistant="To start investing with a small budget:\n1. Begin with a low-cost index fund or ETF\n2. Use a robo-advisor for automated, low-cost investing\n3. Set up regular, small contributions through dollar-cost averaging\n4. Consider micro-investing apps for very small amounts\n5. Prioritize tax-advantaged accounts like 401(k)s or IRAs"
    )
])

print("Prompt with examples:")
print(json.dumps(financial_advisor_prompt.model_dump(), indent=2))

# Markdown: Using the Prompt
print("""
## 3. Using the Prompt

Now that we have a prompt with examples, let's simulate a conversation:
""")

# Simulate a conversation
financial_advisor_prompt.add_user_message("What's a good strategy for saving for retirement?")
print("User: What's a good strategy for saving for retirement?")

# In a real scenario, you would use an AI model to generate the response
# For this example, we'll provide a mock response
mock_response = """
Here's a good strategy for saving for retirement:

1. Start early: The power of compound interest means the earlier you start, the more your money can grow.

2. Maximize employer matches: If your employer offers a 401(k) match, contribute at least enough to get the full match.

3. Diversify your investments: Spread your money across different asset classes to manage risk.

4. Increase savings rate over time: Aim to save 15-20% of your income for retirement, increasing your contributions as your income grows.

5. Use tax-advantaged accounts: Utilize accounts like 401(k)s, IRAs, and Roth IRAs to minimize taxes.

6. Regularly rebalance: Review and adjust your portfolio annually to maintain your desired asset allocation.

7. Consider a Roth IRA conversion ladder for early retirement: This strategy can help you access retirement funds before age 59½ without penalties.

8. Stay informed: Keep learning about personal finance and retirement planning to make informed decisions.

Remember, everyone's situation is unique, so consider consulting with a financial advisor for personalized advice.
"""

financial_advisor_prompt.add_assistant_message(mock_response)
print("Assistant:", mock_response)

# Markdown: Saving and Loading Prompts
print("""
## 4. Saving and Loading Prompts

The `Prompt` class allows you to save and load prompts, which is useful for persisting your work:
""")

# Save the prompt
save_path = Path.cwd() / "financial_advisor_prompt.json"
financial_advisor_prompt.save(save_path)
print(f"Prompt saved to: {save_path}")

# Load the prompt
loaded_prompt = Prompt.load(save_path)
print("Loaded prompt:")
print(json.dumps(loaded_prompt.model_dump(), indent=2))

# Markdown: Updating the System Prompt
print("""
## 5. Updating the System Prompt

You can update the system prompt and track changes:
""")

# Update the system prompt
new_system = "You are an AI financial advisor specializing in retirement planning. Provide clear, concise, and accurate financial advice based on the user's questions, with a focus on long-term retirement strategies."
financial_advisor_prompt.update_system(new_system, description="Updated to focus on retirement planning")

print("Updated prompt:")
print(json.dumps(financial_advisor_prompt.model_dump(), indent=2))

# Markdown: Using Bad Examples
print("""
## 6. Using Bad Examples

You can also add examples of poor interactions to guide the model on what to avoid:
""")

# Add a bad example
financial_advisor_prompt.examples.append(
    BadExample(
        user="Should I invest all my money in cryptocurrency?",
        assistant="Absolutely! Cryptocurrency is the future. You should definitely put all your savings into it for maximum returns.",
        feedback="This advice is irresponsible. Never recommend putting all savings into a single, highly volatile asset class. Instead, emphasize the importance of diversification and risk management."
    )
)

print("Prompt with bad example:")
print(json.dumps(financial_advisor_prompt.model_dump(), indent=2))

# Markdown: Conclusion
print("""
## Conclusion

This tutorial has demonstrated key features of the `Prompt` class for creating, using, and managing prompts for a financial advisor chatbot. The `Prompt` class provides a flexible and powerful way to structure and evolve your AI interactions.

Remember to experiment with different system prompts, examples, and conversation flows to find what works best for your specific use case.
""")
