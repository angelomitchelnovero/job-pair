"""Job description parsing service."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.skills_taxonomy import detect_skills


_YEARS_RE = re.compile(
    r"(\d+)\+?\s*(?:\-\s*\d+\s*)?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?",
    re.IGNORECASE,
)

_REQUIRED_KEYWORDS = [
    "required",
    "must have",
    "must-have",
    "requirements",
    "you should have",
    "you must",
    "we require",
]

_PREFERRED_KEYWORDS = [
    "preferred",
    "nice to have",
    "nice-to-have",
    "bonus",
    "plus",
    "would be great",
    "good to have",
]

_RESPONSIBILITY_HEADERS = [
    "responsibilities",
    "what you'll do",
    "what you will do",
    "your role",
    "role responsibilities",
    "day-to-day",
]

_EDUCATION_KEYWORDS = [
    "bachelor",
    "master",
    "phd",
    "doctorate",
    "degree",
    "mba",
    "bs/",
    "ms/",
    "bs ",
    "ms ",
    "computer science",
]


@dataclass
class JobData:
    title: str = ""
    company: Optional[str] = None
    description: str = ""
    skills_required: List[str] = field(default_factory=list)
    skills_preferred: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    experience_years: Optional[int] = None
    education_required: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "description": self.description,
            "skills_required": self.skills_required,
            "skills_preferred": self.skills_preferred,
            "responsibilities": self.responsibilities,
            "experience_years": self.experience_years,
            "education_required": self.education_required,
        }


class JobParser:
    """Extracts structured fields from a job description."""

    def parse(
        self,
        description: str,
        title: str = "",
        company: Optional[str] = None,
    ) -> JobData:
        data = JobData(
            description=description,
            title=title or self._guess_title(description),
            company=company,
        )

        required_block = self._extract_block(description, _REQUIRED_KEYWORDS)
        preferred_block = self._extract_block(description, _PREFERRED_KEYWORDS)
        responsibilities_block = self._extract_block(description, _RESPONSIBILITY_HEADERS)

        # If neither block found, put all detected skills into required
        if not required_block and not preferred_block:
            required_skills = detect_skills(description)
        else:
            required_skills = detect_skills(required_block) if required_block else []
            preferred_skills = detect_skills(preferred_block) if preferred_block else []
            # Skills not in either explicit block: detect from full text minus preferred
            extra_text = description.replace(preferred_block or "", "")
            extras = detect_skills(extra_text)
            required_skills = list(dict.fromkeys(required_skills + [s for s in extras if s not in preferred_skills]))
            data.skills_preferred = preferred_skills
        data.skills_required = list(dict.fromkeys(required_skills))

        data.responsibilities = self._bullet_lines(responsibilities_block) if responsibilities_block else []
        data.experience_years = self._extract_years(description)
        data.education_required = self._extract_education(description)

        return data

    # ----------------------------------------------------------- utils
    def _guess_title(self, text: str) -> str:
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned and len(cleaned) <= 100:
                return cleaned
        return "Untitled Position"

    def _extract_block(self, text: str, keywords: List[str]) -> str:
        lower = text.lower()
        positions: list[int] = []
        for kw in keywords:
            idx = lower.find(kw)
            if idx >= 0:
                positions.append(idx)
        if not positions:
            return ""
        start = min(positions)
        # Capture up to next blank line or next 1500 chars
        chunk = text[start:]
        end = chunk.find("\n\n")
        if end == -1:
            end = min(len(chunk), 1500)
        return chunk[:end]

    def _bullet_lines(self, block: str) -> List[str]:
        lines: List[str] = []
        for raw in block.splitlines():
            cleaned = raw.strip().lstrip("•-*·—>0123456789. ")
            if cleaned and len(cleaned) > 3:
                lines.append(cleaned)
        return lines

    def _extract_years(self, text: str) -> Optional[int]:
        m = _YEARS_RE.search(text)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                return None
        return None

    def _extract_education(self, text: str) -> Optional[str]:
        lower = text.lower()
        for kw in _EDUCATION_KEYWORDS:
            if kw in lower:
                return kw
        return None
