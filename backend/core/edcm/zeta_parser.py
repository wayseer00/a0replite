from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional


_ZETA_SIGNAL_PATTERN = re.compile(r"ZETA\[(?P<label>[A-Z_]+)\]\s*=\s*(?P<value>.+?)(?=\nZETA\[|\Z)", re.S)
_SECTION_PATTERN = re.compile(r"^##\s+(?P<title>.+)$", re.M)


class ZetaDocument:
    """A parsed canonical edcmbone document with Zeta-signals and sections."""

    def __init__(self, name: str, raw: str) -> None:
        self.name = name
        self.raw = raw
        self._signals: dict[str, str] = {}
        self._sections: list[dict] = []
        self._parse()

    def _parse(self) -> None:
        for m in _ZETA_SIGNAL_PATTERN.finditer(self.raw):
            self._signals[m.group("label")] = m.group("value").strip()
        section_texts: list[tuple[str, int]] = []
        for m in _SECTION_PATTERN.finditer(self.raw):
            section_texts.append((m.group("title"), m.start()))
        for i, (title, start) in enumerate(section_texts):
            end = section_texts[i + 1][1] if i + 1 < len(section_texts) else len(self.raw)
            body = self.raw[start:end].strip()
            self._sections.append({"title": title, "body": body, "offset": start})

    def signal(self, label: str, default: Any = None) -> Any:
        return self._signals.get(label, default)

    def section(self, title_fragment: str) -> Optional[dict]:
        for s in self._sections:
            if title_fragment.lower() in s["title"].lower():
                return s
        return None

    @property
    def signals(self) -> dict[str, str]:
        return dict(self._signals)

    @property
    def sections(self) -> list[dict]:
        return list(self._sections)


class ZetaParser:
    """
    In-house Zeta parser. Processes the canonical edcmbone zip to extract readable documents.
    This is NOT the pip-installed edcmbone stubs — we operate on the raw canonical data.
    """

    def __init__(self) -> None:
        self._docs: dict[str, ZetaDocument] = {}
        self._raw_files: dict[str, str] = {}

    def load_zip(self, zip_bytes: bytes) -> None:
        """Load all text files from the edcmbone canonical zip."""
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            for member in zf.infolist():
                if member.filename.endswith("/") or member.file_size == 0:
                    continue
                try:
                    text = zf.read(member.filename).decode("utf-8", errors="replace")
                    short_name = Path(member.filename).name
                    self._raw_files[member.filename] = text
                    self._docs[short_name] = ZetaDocument(short_name, text)
                    self._docs[member.filename] = self._docs[short_name]
                except Exception:
                    continue

    def get(self, name: str) -> Optional[ZetaDocument]:
        return self._docs.get(name)

    def all_names(self) -> list[str]:
        return [k for k in self._docs if "/" not in k]

    def grep(self, pattern: str, flags: int = re.IGNORECASE) -> list[dict]:
        """Search all docs for a pattern. Returns list of {name, line, text}."""
        results = []
        regex = re.compile(pattern, flags)
        for name, doc in self._docs.items():
            if "/" in name:
                continue
            for i, line in enumerate(doc.raw.splitlines(), 1):
                if regex.search(line):
                    results.append({"name": name, "line": i, "text": line.strip()})
        return results
