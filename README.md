# Foresight

[![PyPI version](https://img.shields.io/pypi/v/foresight-transcribe)](https://pypi.org/project/foresight-transcribe/)
[![PyPI downloads](https://img.shields.io/pypi/dm/foresight-transcribe)](https://pypi.org/project/foresight-transcribe/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/dnoma/foresight)](https://github.com/dnoma/foresight/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/dnoma/foresight?style=social)](https://github.com/dnoma/foresight)

**Turn recorded conversations into structured insights. Automatically.**

Drop an audio file in a folder. Get back a searchable transcript and an AI-extracted summary with key themes, quotes, and follow-up questions.

100% local. No API costs. No data leaves your machine.

---

## The Problem

You record important conversations—interviews, user research calls, sales demos, meetings. Then the audio sits there because:

- Transcription services cost money and take time
- Reading a full transcript is tedious
- The insights you need are buried in 45 minutes of audio
- Organizing files manually is a chore

## The Solution

```
Audio file drops in folder
         ↓
   [3-5 minutes]
         ↓
Transcript.md + Insights.md
         ↓
Original archived automatically
```

**What you get:**

| Output | Contents |
|--------|----------|
| **Transcript** | Full searchable text, YAML metadata, word count |
| **Insights** | Pain points, objections, decision criteria, key quotes, follow-up questions, executive summary |

---

## Use Cases

- **User Research** — Extract patterns from customer interviews
- **Sales Calls** — Capture objections and buying signals
- **Podcasters** — Generate show notes and quotable moments
- **Journalists** — Transcribe interviews with structured highlights
- **Founders** — Process investor/customer conversations at scale
- **Consultants** — Document client discovery sessions
- **Academics** — Transcribe and analyze qualitative research

---

## Install

```bash
pip install foresight-transcribe
```

That's it. Or install from source:

```bash
git clone https://github.com/dnoma/foresight.git
cd foresight
pip install -e .
```

### Setup Ollama (required for insights)

```bash
# Install Ollama
brew install ollama   # macOS
# or: curl -fsSL https://ollama.ai/install.sh | sh  # Linux

# Start and pull model (~4GB)
ollama serve &
ollama pull mistral
```

### Verify installation

```bash
foresight --test
```

---

## Usage

### Watch Mode (recommended)
Leave it running. Drop files in the folder, they process automatically.
```bash
foresight --watch
```

### Single File
Process one recording right now.
```bash
foresight --file meeting.m4a
```

### Batch Mode
Have a backlog? Process everything at once.
```bash
foresight --batch
```

---

## What the Output Looks Like

### Transcript
```markdown
---
filename: customer-call-jan-11.m4a
duration: 34:22
word_count: 4521
model: whisper-medium
---

# Transcript: customer-call-jan-11

The full conversation, searchable and quotable...
```

### Insights
```markdown
## PAIN POINTS
- Manual invoice processing takes 3 days each month
- No visibility into supplier risk until problems occur

## DECISION CRITERIA
- Must integrate with existing SAP system
- Needs to show ROI within 90 days

## KEY QUOTES
- "We've been burned twice by suppliers going bankrupt with no warning"

## FOLLOW-UP QUESTIONS
- What's the current approval workflow for new suppliers?
- Who else is involved in the vendor selection process?

## EXECUTIVE SUMMARY
[2-3 sentence summary of the entire conversation]
```

---

## Directory Structure

Auto-created on first run:

```
~/klavis-interviews/
├── raw/           ← Drop recordings here
├── transcripts/   ← Whisper output
├── insights/      ← LLM-extracted analysis
├── archive/       ← Processed originals
└── processing.log
```

---

## Configuration

Edit the config in `interview_processor.py` (or after install: `~/.local/lib/python*/site-packages/interview_processor.py`):

```python
WHISPER_MODEL = "medium"    # tiny|base|small|medium|large
OLLAMA_MODEL = "mistral"    # or phi3, llama3, etc.
MIN_FILE_SIZE = 100000      # Skip files under 100KB
```

### Customize the extraction prompt

The `EXTRACTION_PROMPT` variable controls what the LLM extracts. Modify it for your use case:

```python
# For sales calls
EXTRACTION_PROMPT = """Extract: objections raised, competitor mentions,
next steps agreed, budget signals..."""

# For user research
EXTRACTION_PROMPT = """Extract: user goals, frustrations,
current workflow, feature requests..."""
```

---

## Options

| Flag | Description |
|------|-------------|
| `-m, --model` | Whisper model size (default: medium) |
| `--skip-insights` | Transcribe only, skip LLM extraction |
| `--keep-original` | Don't move to archive after processing |
| `--dry-run` | Preview what would be processed |
| `--status` | Show pending files and system health |
| `--retry-failed` | Retry previously failed files |
| `--test` | Verify installation works |

---

## System Requirements

- **macOS** (tested) or Linux
- **~6-7GB RAM** during processing (models load/unload automatically)
- **Python 3.9+**
- **~5GB disk** for models (one-time download)

### Processing Time

| Audio Length | Time (M1 Mac) |
|--------------|---------------|
| 5 min | ~45 sec |
| 30 min | ~3 min |
| 60 min | ~6 min |

---

## Why Local?

| | Local (this tool) | Cloud APIs |
|--|-------------------|------------|
| **Cost** | Free | $0.006/min+ |
| **Privacy** | Data stays on device | Uploaded to servers |
| **Speed** | No upload/download | Network dependent |
| **Availability** | Works offline | Requires internet |

A 1-hour recording costs ~$0.36 on cloud transcription. Process 100 interviews and you've saved $36—plus your data never left your laptop.

---

## Supported Formats

`.m4a` `.mp3` `.wav` `.mp4`

Files under 100KB are skipped (filters out accidental recordings).

---

## Troubleshooting

**Ollama not running?**
```bash
ollama serve        # Start the server
ollama ps           # Check if model is loaded
```

**Transcription too slow?**
```bash
foresight --file audio.m4a --model small
```

**Check system status:**
```bash
foresight --status
```

---

## License

MIT

---

## Contributing

PRs welcome. Ideas:
- [ ] Speaker diarization (who said what)
- [ ] Custom prompt templates via config file
- [ ] Web UI for reviewing insights
- [ ] Export to Notion/Obsidian
- [ ] Slack/Discord notifications when processing completes

---

## Support

If this saved you time or money, consider giving it a star. It helps others discover the project.

[![Star this repo](https://img.shields.io/github/stars/dnoma/foresight?style=social)](https://github.com/dnoma/foresight)

Built by [@dnoma](https://github.com/dnoma) — indie dev building tools that save time.
