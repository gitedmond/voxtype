import json
import uuid
from datetime import datetime
from pathlib import Path

HISTORY_PATH = Path(__file__).parent.parent / "history.json"

class HistoryManager:
    def __init__(self, max_items: int = 500):
        self.max_items = max_items
        self._entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if HISTORY_PATH.exists():
            try:
                data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._entries = data
            except Exception as e:
                print(f"[HistoryManager] Error loading history: {e}")
                self._entries = []

    def _save(self) -> None:
        try:
            # Enforce max_items limit
            if len(self._entries) > self.max_items:
                self._entries = self._entries[:self.max_items]
            HISTORY_PATH.write_text(
                json.dumps(self._entries, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[HistoryManager] Error saving history: {e}")

    def add_entry(self, text: str, mode: str = "Dictation", language: str = "en") -> dict:
        """Add a completed dictation entry to history."""
        if not text or not text.strip():
            return {}

        clean_text = text.strip()
        words = clean_text.split()

        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": clean_text,
            "mode": mode,
            "char_count": len(clean_text),
            "word_count": len(words),
            "language": language
        }

        # Prepend newest entry to top
        self._entries.insert(0, entry)
        self._save()
        print(f"[History] Recorded entry ({len(clean_text)} chars, {len(words)} words).")
        return entry

    def get_entries(self, query: str = "") -> list[dict]:
        """Get dictation entries, optionally filtered by search query."""
        if not query or not query.strip():
            return self._entries

        q = query.strip().lower()
        return [
            e for e in self._entries
            if q in e.get("text", "").lower() or q in e.get("mode", "").lower()
        ]

    def clear_history(self) -> None:
        """Clear all dictation history records."""
        self._entries = []
        self._save()
        print("[History] History cleared.")

    def get_stats(self) -> dict:
        """Compute total dictations, total words, and total characters."""
        total_dictations = len(self._entries)
        total_words = sum(e.get("word_count", 0) for e in self._entries)
        total_chars = sum(e.get("char_count", 0) for e in self._entries)
        return {
            "total_dictations": total_dictations,
            "total_words": total_words,
            "total_chars": total_chars
        }
