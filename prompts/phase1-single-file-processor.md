# Phase 1: Single-File Processor - Claude Prompt

Build me a Python script called `process_single.py` that processes a single audio file through transcription and insight extraction.

## Requirements

**USAGE:**
```bash
python process_single.py ~/klavis-interviews/raw/interview-123.m4a
```

**CORE FUNCTIONALITY:**
1. Accept audio file path as CLI argument
2. Validate file:
   - Exists
   - Supported format (.m4a, .wav, .mp3, .mp4)
   - Size > 100KB (skip test recordings)
3. Transcribe using Whisper (medium model)
4. Save transcript to `~/klavis-interviews/transcripts/[filename].md`
5. Send transcript to Ollama for extraction
6. Save insights to `~/klavis-interviews/insights/[filename]-insights.md`
7. Move processed file to `~/klavis-interviews/archive/`
8. Log all steps to `~/klavis-interviews/processing.log`

**TRANSCRIPTION:**
```python
import whisper
model = whisper.load_model("medium")
result = model.transcribe(audio_path)
transcript = result["text"]
```

**OLLAMA EXTRACTION:**
```python
import subprocess
result = subprocess.run(
    ["ollama", "run", "mistral", prompt],
    capture_output=True,
    text=True
)
insights = result.stdout
```

**EXTRACTION PROMPT:**
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

**OUTPUT FORMAT - TRANSCRIPT:**
```markdown
---
filename: interview-name.m4a
processed_date: 2025-01-11 14:30:22
duration: 45:23
model: whisper-medium
---

# Transcript: interview-name

[Full transcription text here...]
```

**OUTPUT FORMAT - INSIGHTS:**
```markdown
---
source: interview-name.m4a
processed_date: 2025-01-11 14:35:10
llm_model: mistral
---

# Interview Insights: interview-name

[Extracted insights here...]
```

**ERROR HANDLING:**
- If file not found: Print error and exit
- If Ollama not running: Print helpful message with instructions
- If transcription fails: Log error, don't crash
- If disk full: Handle gracefully with clear message

**PROGRESS INDICATORS:**
```
[2025-01-11 14:30:22] 📁 Processing: interview-john-tan.m4a
[2025-01-11 14:30:23] 🎙️  Transcribing... (this may take 2-3 minutes)
[2025-01-11 14:32:45] ✅ Transcript saved
[2025-01-11 14:32:46] 🧠 Extracting insights...
[2025-01-11 14:33:15] ✅ Insights saved
[2025-01-11 14:33:16] 📦 Moved to archive
[2025-01-11 14:33:16] ✨ Complete!
```

**DEPENDENCIES:**
- whisper (openai-whisper)
- subprocess (for Ollama)
- pathlib, logging, argparse, shutil

Build this as a complete, runnable script with proper error handling and logging.
