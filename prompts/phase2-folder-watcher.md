# Phase 2: Folder Watcher - Claude Prompt

Build me a Python script called `watch_interviews.py` that continuously monitors a folder and automatically processes new audio files.

## Requirements

**CORE FUNCTIONALITY:**
1. Monitor `~/klavis-interviews/raw/` folder for new files
2. When a new `.m4a`, `.wav`, `.mp3`, or `.mp4` file appears:
   - Wait 5 seconds (ensure file is fully copied/synced)
   - Verify file size is > 100KB
   - Process the file using the same logic as phase 1:
     * Transcribe with Whisper
     * Extract insights with Ollama
     * Save outputs
     * Move to archive
3. Continue watching after processing completes
4. Handle multiple files appearing simultaneously (queue them)
5. Run indefinitely until Ctrl+C

**REUSE PROCESSING LOGIC:**
Import or copy the processing functions from `process_single.py`:
- File validation
- Whisper transcription
- Ollama extraction
- File moving
- Output formatting

Or create a shared module that both scripts use.

**ERROR HANDLING:**
- If processing one file fails, log error and continue watching
- Don't crash the watcher on any single file error
- Handle permission errors gracefully
- Handle disk full errors gracefully
- If Ollama is not running, log warning every 5 minutes but keep watching

**DUPLICATE PREVENTION:**
- Before processing, check if file already exists in archive/
- If duplicate found, log warning and skip processing
- Use filename matching (exact match)

**STARTUP BEHAVIOR:**
When script starts:
1. Check all required directories exist (create if needed)
2. Test Ollama connection (warn if not available)
3. Print status message:
```
[2025-01-11 14:30:00] 👀 Watching ~/klavis-interviews/raw/
[2025-01-11 14:30:00] ✅ Ollama is running
[2025-01-11 14:30:00] 📂 Ready to process new recordings
[2025-01-11 14:30:00] Press Ctrl+C to stop
```

**PROGRESS INDICATORS:**
Same as Phase 1, but with file context:
```
[2025-01-11 14:35:12] 🆕 New file detected: interview-jane-doe.m4a
[2025-01-11 14:35:17] 📁 Processing: interview-jane-doe.m4a
[2025-01-11 14:35:18] 🎙️  Transcribing... (this may take 2-3 minutes)
...
[2025-01-11 14:37:45] ✨ Complete! Watching for next file...
```

**GRACEFUL SHUTDOWN:**
When user presses Ctrl+C:
```
[2025-01-11 15:00:00] 🛑 Shutdown requested
[2025-01-11 15:00:00] 📊 Processed 3 files this session
[2025-01-11 15:00:00] 👋 Goodbye!
```

**USAGE:**
```bash
# Start watching
python watch_interviews.py

# Run in background (optional)
nohup python watch_interviews.py &
```

**DEPENDENCIES:**
- watchdog (for file system monitoring)
- whisper
- subprocess (for Ollama)
- pathlib, logging, time, signal

**WATCHDOG IMPLEMENTATION:**
Use `watchdog.observers.Observer` and `watchdog.events.FileSystemEventHandler`:
- Monitor for `created` and `moved_to` events (handles both manual copy and iCloud sync)
- Filter for supported audio formats
- Debounce rapid events (wait 5 seconds after file appears)

**LOGGING:**
- Log to both console and `~/klavis-interviews/processing.log`
- Include timestamps on all log lines
- Log level: INFO for progress, ERROR for failures

**CODE QUALITY:**
- Clean, well-commented code
- Production-ready error handling
- Separate concerns (watching vs processing)
- Easy to debug

**OPTIONAL ENHANCEMENT:**
Add a `--backlog` flag that processes any existing files in `raw/` before starting to watch:
```bash
python watch_interviews.py --backlog
```

Build this as a complete, runnable script. Make it robust enough to run for days without crashing.
