```python
[
    # ... previous messages ...
    # User request
    ModelRequest(
        parts=[
            UserPromptPart(
                content='enemies detected on planet knd. send out a warning to the team and get 1 plasma rifle and 1 ion blaster ready',
                timestamp=datetime.datetime(2025, 9, 7, 22, 15, 53, 788644, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - issue alien warning
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='issue_alien_warning',
                args={'location': 'planet knd', 'level': 3},
                tool_call_id='pyd_ai_9066974bd75d4d0e927c8fcdf1e01449'
            )
        ],
        usage=RequestUsage(
            input_tokens=1020,
            output_tokens=226,
            details={'thoughts_tokens': 202, 'text_prompt_tokens': 1020}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 22, 15, 55, 908707, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='GwS-aKvWLpf6nsEPg5C1oQ8'
    ),
    # Tool return - warning issued
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='issue_alien_warning',
                content='[Alert] Alien activity detected at planet knd. All units standby. Threat level 3/5.',
                tool_call_id='pyd_ai_9066974bd75d4d0e927c8fcdf1e01449',
                timestamp=datetime.datetime(2025, 9, 7, 22, 15, 55, 910805, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - arm plasma rifle
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='arm_weapon_system',
                args={'units': 1, 'weapon_name': 'plasma_rifle'},
                tool_call_id='pyd_ai_9cf1af4caeaf4adf81622e0cab5e6874'
            )
        ],
        usage=RequestUsage(
            input_tokens=1083,
            cache_read_tokens=713,
            output_tokens=26,
            details={'cached_content_tokens': 713, 'text_prompt_tokens': 1083, 'text_cache_tokens': 713}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 22, 15, 56, 620564, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='HAS-aO35INOykdUP2bLMoA8'
    ),
    # Tool return - plasma rifle armed
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='arm_weapon_system',
                content=True,
                tool_call_id='pyd_ai_9cf1af4caeaf4adf81622e0cab5e6874',
                timestamp=datetime.datetime(2025, 9, 7, 22, 15, 56, 621712, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - arm ion blaster
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='arm_weapon_system',
                args={'weapon_name': 'ion_blaster', 'units': 1},
                tool_call_id='pyd_ai_5f385f440ace4b828bbc103e3bd56419'
            )
        ],
        usage=RequestUsage(
            input_tokens=1127,
            cache_read_tokens=716,
            output_tokens=27,
            details={'cached_content_tokens': 716, 'text_prompt_tokens': 1127, 'text_cache_tokens': 716}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 22, 15, 57, 338492, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='HQS-aKeBENu5nsEP3qbZmQ8'
    ),
    # Tool return - ion blaster armed
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='arm_weapon_system',
                content=True,
                tool_call_id='pyd_ai_5f385f440ace4b828bbc103e3bd56419',
                timestamp=datetime.datetime(2025, 9, 7, 22, 15, 57, 339748, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI final response
    ModelResponse(
        parts=[
            TextPart(content='Alien activity detected on Planet KND. Threat level 3. Plasma rifle and Ion blaster allocated.')
        ],
        usage=RequestUsage(
            input_tokens=1172,
            cache_read_tokens=719,
            output_tokens=20,
            details={'cached_content_tokens': 719, 'text_prompt_tokens': 1172, 'text_cache_tokens': 719}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 22, 15, 58, 54299, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='HgS-aL5g_YWR1Q-9yMTACw'
    )
]
```