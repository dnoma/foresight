#!/usr/bin/env python3
"""
Interview Folder Watcher
Monitors a folder for new audio files and automatically processes them.

Usage:
    python watch_interviews.py           # Start watching
    python watch_interviews.py --backlog # Process existing files first, then watch

    # Run in background (optional)
    nohup python watch_interviews.py &
"""

import argparse
import logging
import signal
import sys
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
except ImportError:
    print("❌ watchdog not installed. Run: pip install watchdog")
    sys.exit(1)

# Import from process_single.py (Phase 1)
from process_single import (
    BASE_DIR,
    RAW_DIR,
    ARCHIVE_DIR,
    SUPPORTED_FORMATS,
    MIN_FILE_SIZE_KB,
    LOG_FILE,
    create_directories,
    check_ollama_running,
    process_file,
)

# Configuration
FILE_SETTLE_TIME = 5  # Seconds to wait after file appears
QUEUE_CHECK_INTERVAL = 1  # Seconds between queue checks
OLLAMA_WARNING_INTERVAL = 300  # 5 minutes between Ollama warnings


def timestamp() -> str:
    """Return formatted timestamp for display."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def setup_watcher_logging() -> logging.Logger:
    """Configure logging for the watcher (both console and file)."""
    logger = logging.getLogger("watch_interviews")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(console_format)
    logger.addHandler(file_handler)

    return logger

# Global state
processing_queue = deque()
processed_files: Set[str] = set()
files_processed_count = 0
shutdown_requested = False
queue_lock = threading.Lock()
last_ollama_warning = 0


class InterviewFileHandler(FileSystemEventHandler):
    """Handle file system events for new interview files."""

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.pending_files = {}  # Track files waiting to settle

    def _is_supported_file(self, path: str) -> bool:
        """Check if file has a supported audio format."""
        return Path(path).suffix.lower() in SUPPORTED_FORMATS

    def _schedule_processing(self, file_path: str):
        """Schedule a file for processing after settle time."""
        path = Path(file_path)

        if not self._is_supported_file(file_path):
            return

        # Debounce: if already pending, update the time
        self.pending_files[file_path] = time.time()

        # Start a timer thread for this file
        def check_and_queue():
            time.sleep(FILE_SETTLE_TIME)

            # Only queue if this file is still pending and not modified since
            if file_path in self.pending_files:
                scheduled_time = self.pending_files.get(file_path, 0)
                if time.time() - scheduled_time >= FILE_SETTLE_TIME - 0.5:
                    del self.pending_files[file_path]
                    self._add_to_queue(path)

        thread = threading.Thread(target=check_and_queue, daemon=True)
        thread.start()

    def _add_to_queue(self, file_path: Path):
        """Add file to processing queue if valid."""
        global processed_files

        # Skip if already processed or queued
        if str(file_path) in processed_files:
            return

        # Validate file exists and meets size requirement
        if not file_path.exists():
            return

        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb < MIN_FILE_SIZE_KB:
            self.logger.warning(
                f"⚠️  Skipping {file_path.name}: too small ({file_size_kb:.1f}KB)"
            )
            return

        with queue_lock:
            if str(file_path) not in processed_files:
                processing_queue.append(file_path)
                processed_files.add(str(file_path))
                self.logger.info(f"🆕 New file detected: {file_path.name}")

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        self._schedule_processing(event.src_path)

    def on_moved(self, event):
        """Handle file move events (covers iCloud sync, etc.)."""
        if event.is_directory:
            return
        self._schedule_processing(event.dest_path)


def check_duplicate(file_path: Path) -> bool:
    """Check if file already exists in archive."""
    archive_path = ARCHIVE_DIR / file_path.name
    return archive_path.exists()


def process_queue(logger):
    """Process files from the queue continuously."""
    global files_processed_count, shutdown_requested, last_ollama_warning

    while not shutdown_requested:
        file_path = None

        with queue_lock:
            if processing_queue:
                file_path = processing_queue.popleft()

        if file_path:
            try:
                # Check for duplicate before processing
                if check_duplicate(file_path):
                    logger.warning(f"⚠️  Duplicate found in archive: {file_path.name} - skipping")
                else:
                    success = process_file(file_path)
                    if success:
                        files_processed_count += 1
                logger.info(f"[{timestamp()}] ✨ Complete! Watching for next file...")
            except Exception as e:
                logger.error(f"❌ Error processing {file_path.name}: {e}")
                logger.info("🔄 Continuing to watch for new files...")
        else:
            # No files to process, check Ollama periodically
            current_time = time.time()
            if current_time - last_ollama_warning > OLLAMA_WARNING_INTERVAL:
                if not check_ollama_running():
                    logger.warning(f"[{timestamp()}] ⚠️  Ollama is not running - insights will be skipped")
                last_ollama_warning = current_time

            time.sleep(QUEUE_CHECK_INTERVAL)


def process_backlog(logger):
    """Process any existing files in the raw directory."""
    existing_files = []

    for ext in SUPPORTED_FORMATS:
        existing_files.extend(RAW_DIR.glob(f"*{ext}"))
        existing_files.extend(RAW_DIR.glob(f"*{ext.upper()}"))

    if not existing_files:
        logger.info("📂 No backlog files to process")
        return 0

    logger.info(f"📚 Found {len(existing_files)} file(s) in backlog")

    processed = 0
    for file_path in sorted(existing_files, key=lambda f: f.stat().st_mtime):
        if shutdown_requested:
            break

        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb < MIN_FILE_SIZE_KB:
            logger.warning(f"⚠️  Skipping {file_path.name}: too small")
            continue

        # Check for duplicate
        if check_duplicate(file_path):
            logger.warning(f"⚠️  Duplicate found in archive: {file_path.name} - skipping")
            continue

        try:
            if process_file(file_path):
                processed += 1
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")

    logger.info(f"📚 Backlog complete: processed {processed}/{len(existing_files)} files")
    return processed


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    shutdown_requested = True


def main():
    global files_processed_count, shutdown_requested

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Monitor folder for new interview recordings and process them"
    )
    parser.add_argument(
        "--backlog",
        action="store_true",
        help="Process existing files in raw/ before starting to watch"
    )
    args = parser.parse_args()

    # Setup
    create_directories()
    logger = setup_watcher_logging()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Startup messages
    logger.info(f"👀 Watching {RAW_DIR}/")

    if check_ollama_running():
        logger.info("✅ Ollama is running")
    else:
        logger.warning("⚠️  Ollama is not running - insights will be skipped")

    # Process backlog if requested
    if args.backlog:
        logger.info("📚 Processing backlog first...")
        backlog_count = process_backlog(logger)
        files_processed_count += backlog_count
        if shutdown_requested:
            logger.info("🛑 Shutdown during backlog processing")
            logger.info(f"📊 Processed {files_processed_count} files this session")
            logger.info("👋 Goodbye!")
            return

    logger.info("📂 Ready to process new recordings")
    logger.info("Press Ctrl+C to stop")

    # Setup file watcher
    event_handler = InterviewFileHandler(logger)
    observer = Observer()
    observer.schedule(event_handler, str(RAW_DIR), recursive=False)

    # Start observer
    observer.start()

    # Start queue processor in main thread
    try:
        process_queue(logger)
    except KeyboardInterrupt:
        shutdown_requested = True
    finally:
        # Graceful shutdown
        logger.info("🛑 Shutdown requested")
        observer.stop()
        observer.join(timeout=5)

        logger.info(f"📊 Processed {files_processed_count} files this session")
        logger.info("👋 Goodbye!")


if __name__ == "__main__":
    main()
