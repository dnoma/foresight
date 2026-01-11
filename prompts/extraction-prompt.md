# Interview Extraction Prompt

This prompt is sent to Ollama (Mistral) to extract structured insights from interview transcripts.

## Prompt Template

```
You are analyzing a procurement stakeholder interview transcript. Extract the following in structured markdown format:

## PAIN POINTS
- [List specific problems mentioned with context]

## CURRENT WORKAROUNDS
- [How they handle issues today]

## RISK PATTERNS
- [Recurring failures or vulnerabilities observed]

## OBJECTIONS/CONCERNS
- [Hesitations about potential solutions]

## DECISION CRITERIA
- [What would make them buy/pilot a solution]

## FOLLOW-UP QUESTIONS
- [5-7 specific questions to ask in next conversation]

## KEY QUOTES
- "[Verbatim quotes worth preserving]"

## EXECUTIVE SUMMARY
- [2-3 sentence summary of the conversation]

TRANSCRIPT:
{transcript_text}
```

## Usage in Code

```python
EXTRACTION_PROMPT = """You are analyzing a procurement stakeholder interview transcript. Extract the following in structured markdown format:

## PAIN POINTS
- [List specific problems mentioned with context]

## CURRENT WORKAROUNDS
- [How they handle issues today]

## RISK PATTERNS
- [Recurring failures or vulnerabilities observed]

## OBJECTIONS/CONCERNS
- [Hesitations about potential solutions]

## DECISION CRITERIA
- [What would make them buy/pilot a solution]

## FOLLOW-UP QUESTIONS
- [5-7 specific questions to ask in next conversation]

## KEY QUOTES
- "[Verbatim quotes worth preserving]"

## EXECUTIVE SUMMARY
- [2-3 sentence summary of the conversation]

TRANSCRIPT:
{transcript_text}"""

# Format with actual transcript
prompt = EXTRACTION_PROMPT.format(transcript_text=transcript)

# Send to Ollama
result = subprocess.run(
    ["ollama", "run", "mistral", prompt],
    capture_output=True,
    text=True,
    timeout=300
)
insights = result.stdout
```

## Section Descriptions

| Section | Purpose |
|---------|---------|
| **PAIN POINTS** | Specific problems, frustrations, or challenges mentioned by the interviewee |
| **CURRENT WORKAROUNDS** | How they currently handle issues without a proper solution |
| **RISK PATTERNS** | Recurring failures, vulnerabilities, or risks they've observed |
| **OBJECTIONS/CONCERNS** | Hesitations about potential solutions or changes |
| **DECISION CRITERIA** | What would make them buy, pilot, or adopt a solution |
| **FOLLOW-UP QUESTIONS** | Specific questions to ask in the next conversation |
| **KEY QUOTES** | Verbatim quotes worth preserving for reports or presentations |
| **EXECUTIVE SUMMARY** | 2-3 sentence summary of the entire conversation |

## Customization

To customize the extraction for different interview types, modify the sections above. For example:

### Product Feedback Interviews
- Replace "DECISION CRITERIA" with "FEATURE REQUESTS"
- Add "COMPETITOR MENTIONS" section

### User Research Interviews
- Add "USER GOALS" section
- Add "MENTAL MODELS" section

### Sales Discovery Calls
- Add "BUDGET INDICATORS" section
- Add "TIMELINE" section
- Add "STAKEHOLDERS MENTIONED" section
