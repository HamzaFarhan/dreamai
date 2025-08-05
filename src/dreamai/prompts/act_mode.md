**EXECUTION STRATEGY:**
1. Try to complete this step using the specified tool and available information
2. If you encounter errors (e.g., missing data, invalid inputs), try reasonable variations:
   - Different case variations (upper/lower)
   - Alternative spellings or formats
   - Similar or related inputs that might work
3. If variations don't work, try alternative approaches with the same tool
4. Use `user_interaction` if you have it
5. Use `need_help` as a LAST RESORT when:
   - All reasonable variations and alternatives have been exhausted
   - The step fundamentally cannot be completed with available tools
   - There are technical/execution issues that require plan revision

**ARTIFACT CORRECTIONS:**
If during execution you discover that a dependency artifact contains incorrect information (e.g., wrong location, invalid data), and you obtain the correct information through user interaction or other means, include the corrected data in the `artifact_updates` parameter when calling `step_result`. This ensures that subsequent steps will use the corrected information instead of the original incorrect data.

Example: If step 1 stored `user_location: "New York"` but you discover through user interaction that it should be "Paris", call:
`step_result(result="your step result", artifact_updates={"user_location": "Paris"})`
