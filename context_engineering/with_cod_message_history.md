```python
[
    # ... previous messages ...
    # User request
    ModelRequest(
        parts=[
            UserPromptPart(
                content='what is point 18 in our code of conduct?',
                timestamp=datetime.datetime(2025, 9, 7, 21, 59, 9, 205599, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - read code of conduct
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='read_code_of_conduct',
                args={},
                tool_call_id='pyd_ai_9da20f22121c456196743506fd145ee4'
            )
        ],
        usage=RequestUsage(
            input_tokens=618,
            output_tokens=14,
            details={'text_prompt_tokens': 618}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 59, 10, 624485, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='LgC-aNuBIuOznsEPrJz9gAw'
    ),
    # Tool return - code of conduct content
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='read_code_of_conduct',
                content='''
# Hero Squad Code of Conduct

1. Always be battle-ready and arrive at mission briefings on time.
2. Respect fellow heroes, allies, and our base of operations.
3. Keep comms clear, professional, and mission-focused.
4. Complete your assigned quests and report results promptly.
5. Wear the appropriate armor or disguise for each mission.
6. Guard secret intel with your life—no leaks to alien spies.
7. Use squad gadgets and weapons responsibly.
8. Report strange signals, anomalies, or alien sightings ASAP.
9. Zero tolerance for betrayal, dishonor, or abandoning teammates.
10. Recharge only during designated rest cycles.
11. Follow all safety protocols in battle and training sims.
12. Own your mistakes—heroes take responsibility.
13. No disappearing without notifying Command.
14. Keep your gear and locker spotless.
15. Share intel and tactics in team huddles.
16. No holo-scrolling or personal calls mid-battle.
17. Secure approval before warp jumps or time off.
18. Meet mission deadlines and uphold quality standards.
19. Honor truth, courage, and loyalty at all times.
20. Breaking the Code may result in exile from the squad.
''',
                tool_call_id='pyd_ai_9da20f22121c456196743506fd145ee4',
                timestamp=datetime.datetime(2025, 9, 7, 21, 59, 10, 626637, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI final response
    ModelResponse(
        parts=[
            TextPart(content='Point 18 in the Code of Conduct states: "Meet mission deadlines and uphold quality standards."')
        ],
        usage=RequestUsage(
            input_tokens=972,
            cache_read_tokens=698,
            output_tokens=20,
            details={'cached_content_tokens': 698, 'text_prompt_tokens': 972, 'text_cache_tokens': 698}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 59, 11, 539797, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='LwC-aPPxG9mC7M8P0NLp6Q4'
    )
]
```