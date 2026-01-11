# Phase 3: Unified Processor - Claude Prompt

Build me a production-ready Python script called `interview_processor.py` that combines all processing modes into a single unified tool.

## Requirements

**USAGE:**
```bash
# Automatic mode (continuous watcher)
python interview_processor.py --watch

# Manual mode (single file)
python interview_processor.py --file path/to/interview.m4a

# Process all files in raw folder once
python interview_processor.py --batch

# Show current status
python interview_processor.py --status

# Retry failed files
python interview_processor.py --retry-failed

# Test installation
python interview_processor.py --test
```

**CLI OPTIONS:**
```
-w, --watch          Monitor folder continuously for new files
-f, --file FILE      Process a specific file
-b, --batch          Process all files in raw/ folder once
--status             Show current status of directories
--retry-failed       Retry processing of previously failed files
--test               Run a test to verify installation

-m, --model MODEL    Whisper model: tiny, base, small, medium, large (default: medium)
--skip-insights      Transcribe only, skip LLM extraction
--keep-original      Don't move files to archive after processing
--dry-run            Show what would be processed without processing
-v, --verbose        Enable verbose debug output
```

**DIRECTORY STRUCTURE:**
```
~/klavis-interviews/
├── raw/              # Drop iPhone recordings here
├── transcripts/      # Whisper transcription outputs
├── insights/         # LLM-extracted structured insights
├── archive/          # Successfully processed files
├── failed/           # Files that failed processing
├── processing.log    # Activity log (with rotation)
└── failed_files.json # Tracks failed files for retry
```

**CORE FEATURES:**

1. **Data Classes for Results:**
   - ProcessingResult: success, filepath, error_message, transcript_path, insights_path, word_count, section_count, duration_seconds, processing_time
   - SessionStats: files_processed, files_failed, total_time, errors list

2. **Logging with Rotation:**
   - Use RotatingFileHandler (10MB max, 3 backups)
   - Log to both console and file
   - Verbose mode for debug output

3. **Validation Functions:**
   - validate_file(): Check exists, format, size
   - check_ollama_running(): Verify Ollama and model available
   - check_disk_space(): Warn if < 1GB free
   - check_whisper_available(): Verify whisper installed

4. **Processing Pipeline:**
   - transcribe_audio(): Use Whisper with configurable model
   - extract_insights(): Send to Ollama with timeout
   - save_transcript(): Markdown with YAML frontmatter
   - save_insights(): Markdown with YAML frontmatter
   - move_to_archive(): Handle duplicate filenames

5. **Failed File Tracking:**
   - Record failures to failed_files.json
   - Track error message and attempt count
   - Support retry with --retry-failed

6. **Status Command:**
   - Show counts: raw, transcripts, insights, archive
   - Show failed files with errors
   - Check dependency status

7. **Installation Test:**
   - Check all dependencies
   - Create test audio using macOS `say` command
   - Process through full pipeline
   - Clean up test files

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
processed_date: 2025-01-11T14:30:22
duration: 45:23
word_count: 2847
model: whisper-medium
---

# Transcript: interview-name

[Full transcription text here...]
```

**OUTPUT FORMAT - INSIGHTS:**
```markdown
---
source: interview-name.m4a
processed_date: 2025-01-11T14:35:10
llm_model: mistral
section_count: 8
---

# Interview Insights: interview-name

[Extracted insights here...]
```

**PROGRESS INDICATORS:**
```
[2025-01-11 14:30:22] 📁 Processing: interview-john-tan.m4a (1 of 5)
[2025-01-11 14:30:23] 🎙️  Transcribing with whisper-medium...
[2025-01-11 14:32:45] ✅ Transcript saved (2847 words)
[2025-01-11 14:32:46] 🧠 Extracting insights with mistral...
[2025-01-11 14:33:15] ✅ Insights saved (8 sections)
[2025-01-11 14:33:16] 📦 Moved to archive
[2025-01-11 14:33:16] ✨ Complete! (2m 54s)
```

**BATCH SUMMARY:**
```
============================================================
Batch Processing Complete
============================================================
✅ Processed: 5
❌ Failed: 1
⏱️  Total time: 14m 32s
📈 Average per file: 2m 54s

Failures:
  • interview-corrupted.m4a: Transcription failed
```

**WATCH MODE SESSION STATS:**
```
[2025-01-11 15:00:00] 📊 Session Statistics:
  ✅ Files processed: 8
  ⏱️  Total time: 23m 12s
  📈 Average per file: 2m 54s
  ❌ Errors: 0
```

**ERROR HANDLING:**
- Never crash the watcher on single file errors
- Track failed files for retry
- Check Ollama before processing (offer --skip-insights)
- Handle disk space warnings
- Graceful shutdown with Ctrl+C

**DEPENDENCIES:**
- whisper (openai-whisper)
- watchdog
- subprocess, pathlib, logging, argparse, shutil, signal, json, dataclasses

**CODE QUALITY:**
- Use dataclasses for structured data
- Type hints throughout
- Clean separation of concerns
- Comprehensive docstrings
- Production-ready error handling

Build this as a complete, production-ready script that can run reliably for extended periods.
