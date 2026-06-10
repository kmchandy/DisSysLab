# dissyslab/components/sources/audio_folder_source.py

"""
AudioFolderSource: reads audio clips from a folder and emits one
message per file.

Each message carries the file's path and a short label. The
audio bytes are *not* loaded by the source — downstream agents
(classifiers, transcribers, loudness meters, …) open the file
themselves on demand. This keeps the message queue light and lets
each agent decide how to decode the audio.

This is the source for the ``backyard_birds`` gallery office,
where each clip is passed to a BirdNET classifier that emits one
detection per identified species.

Usage in office.md::

    Sources: audio_folder(path="./samples/", glob="*.mp3", max_files=10)

The default ``glob`` accepts both ``.mp3`` and ``.wav`` files.

An empty folder is *not* an error — the source prints a friendly
note saying where to drop clips and then signals end-of-stream so
the network shuts down cleanly. Users running the office for the
first time should see a helpful diagnostic, not a traceback.

Requirements:
    None. The source itself only reads filenames; decoding the
    audio is the downstream agent's responsibility.
"""

from __future__ import annotations

from pathlib import Path


# Audio extensions we recognise by default. Used when ``glob`` is
# left at its default value of "*". Explicit globs ("*.mp3") win.
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}


class AudioFolderSource:
    """Emit one message per audio file found in a folder.

    Parameters
    ----------
    path:
        Directory containing audio clips. Resolved relative to the
        current working directory (the office's launch directory).
    glob:
        Filename pattern. Defaults to ``"*"`` which is filtered by
        the audio extensions above. Pass ``"*.mp3"`` to restrict
        to one format.
    max_files:
        Stop after this many files. ``None`` means emit every
        matching file.

    Yields
    ------
    A dict per file with::

        {
            "path":     "/abs/path/to/clip.mp3",
            "filename": "clip.mp3",
            "title":    "clip.mp3",
            "source":   "audio_folder",
            "index":    1,        # 1-based position
            "total":    7,        # total files matched
        }

    Returns ``None`` when the folder is empty or all matching files
    have been emitted. The framework treats ``None`` as end-of-
    stream and shuts the network down cleanly.
    """

    def __init__(
        self,
        path: str = "./samples/",
        glob: str = "*",
        max_files: int | None = None,
    ):
        self.path = Path(path)
        self.glob = glob
        self.max_files = max_files
        self._files = self._find_files()
        self._index = 0
        self._announced_empty = False

    def _find_files(self) -> list[Path]:
        """Return the sorted list of audio files in ``self.path``.

        Missing folder or empty folder are *not* errors — they
        produce a friendly note on first call and an empty list.
        """
        if not self.path.exists() or not self.path.is_dir():
            return []
        matches = sorted(self.path.glob(self.glob))
        if self.glob == "*":
            matches = [
                f for f in matches
                if f.suffix.lower() in _AUDIO_EXTENSIONS
            ]
        return [f for f in matches if f.is_file()]

    def _announce_empty_once(self) -> None:
        if self._announced_empty:
            return
        self._announced_empty = True
        resolved = self.path.resolve()
        print(
            f"[audio_folder] no audio files matching {self.glob!r} "
            f"in {resolved}."
        )
        print(
            "[audio_folder] Drop one or more "
            f"{', '.join(sorted(_AUDIO_EXTENSIONS))} clips into "
            "that folder and rerun."
        )
        print(
            "[audio_folder] Free Creative-Commons bird recordings: "
            "https://www.xeno-canto.org/"
        )

    def run(self):
        """Emit the next audio file, or ``None`` when exhausted."""
        limit = (
            self.max_files
            if self.max_files is not None
            else len(self._files)
        )
        total = min(len(self._files), limit)

        if self._index >= total:
            if total == 0:
                self._announce_empty_once()
            return None

        f = self._files[self._index]
        self._index += 1
        return {
            "path":     str(f.resolve()),
            "filename": f.name,
            "title":    f.name,
            "source":   "audio_folder",
            "index":    self._index,
            "total":    total,
        }


# ── Self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "./samples/"
    src = AudioFolderSource(path=folder)
    print(f"AudioFolderSource — Self Test ({folder})")
    print("=" * 60)
    count = 0
    while True:
        msg = src.run()
        if msg is None:
            break
        print(f"  {msg['index']:>3}/{msg['total']:<3}  {msg['filename']}")
        count += 1
    print()
    print(f"Emitted {count} file(s), then returned None.")
