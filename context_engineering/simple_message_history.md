```python
[
    # User request
    ModelRequest(
        parts=[
            UserPromptPart(
                content='list all the heroes in our squad',
                timestamp=datetime.datetime(2025, 9, 7, 21, 47, 29, 544777, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - list squad members
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='list_squad_members',
                args={},
                tool_call_id='pyd_ai_2dfaa46381a446119a5e8787317c37e5'
            )
        ],
        usage=RequestUsage(
            input_tokens=543,
            output_tokens=76,
            details={'thoughts_tokens': 63, 'text_prompt_tokens': 543}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 47, 31, 929876, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='c_29aJyrN-j_nsEPsJ67kQM'
    ),
    # Tool return - squad member list
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='list_squad_members',
                content=['Aegis', 'Nova', 'Quark', 'Valkyr'],
                tool_call_id='pyd_ai_2dfaa46381a446119a5e8787317c37e5',
                timestamp=datetime.datetime(2025, 9, 7, 21, 47, 31, 932012, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI final response
    ModelResponse(
        parts=[
            TextPart(content='Squad members: Aegis, Nova, Quark, Valkyr.')
        ],
        usage=RequestUsage(
            input_tokens=591,
            output_tokens=13,
            details={'text_prompt_tokens': 591}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 47, 32, 745208, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='dP29aOfNLNnrnsEPvvSc8Aw'
    )
]
```