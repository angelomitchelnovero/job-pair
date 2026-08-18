"""Resume parsing service - extracts sections/skills from PDF or raw text."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

from app.core.exceptions import ProcessingError
from app.services.skills_taxonomy import detect_skills
from app.services.text_processing import clean_text, normalize_text


# Header keywords used to find sections
_SECTION_HEADERS: Dict[str, List[str]] = {
    "summary": ["summary", "objective", "professional summary", "profile"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
    ],
    "education": ["education", "academic", "qualifications"],
    "projects": ["projects", "personal projects", "academic projects", "key projects"],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "professional certifications",
    ],
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().\-]{7,}\d)")
# Years of experience hint
_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience", re.IGNORECASE)


@dataclass
class ResumeData:
    raw_text: str
    sections: Dict[str, str] = field(default_factory=dict)
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    experience: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    years_experience_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "sections": self.sections,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "experience": self.experience,
            "education": self.education,
            "projects": self.projects,
            "certifications": self.certifications,
            "years_experience_estimate": self.years_experience_estimate,
        }


class ResumeParser:
    """Parses PDF resumes or pasted text into structured ResumeData."""

    def parse_pdf(self, file_bytes: bytes) -> ResumeData:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = [(p.extract_text() or "") for p in pdf.pages]
        except Exception as exc:  # pragma: no cover - depends on file system
            raise ProcessingError(
                f"Failed to read PDF: {exc}", details={"hint": "Check that the file is a valid PDF."}
            ) from exc

        text = "\n".join(pages_text)
        if not text.strip():
            raise ProcessingError(
                "PDF contained no extractable text. It may be a scanned image.",
                details={"hint": "Try a text-based PDF or paste the resume text manually."},
            )
        return self.parse_text(text)

    def parse_text(self, text: str) -> ResumeData:
        data = ResumeData(raw_text=text)
        data.sections = self._split_sections(text)
        data.full_name = self._guess_name(text)
        data.email = self._find_email(text)
        data.phone = self._find_phone(text)
        data.skills = self._extract_skills(data.sections.get("skills", ""), text)
        data.experience = self._extract_experience(data.sections.get("experience", ""))
        data.education = self._extract_education(data.sections.get("education", ""))
        data.projects = self._extract_projects(data.sections.get("projects", ""))
        data.certifications = self._extract_certifications(data.sections.get("certifications", ""))
        data.years_experience_estimate = self._estimate_years(text)
        return data

    # ------------------------------------------------------------------ utils
    def _split_sections(self, text: str) -> Dict[str, str]:
        lines = [ln.rstrip() for ln in text.splitlines()]
        positions: List[Tuple[str, int]] = []
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if not stripped or len(stripped) > 60:
                continue
            for canonical, aliases in _SECTION_HEADERS.items():
                if stripped in aliases or any(stripped == a for a in aliases):
                    positions.append((canonical, i))
                    break

        if not positions:
            return {"body": text}

        # Sort by position. If duplicates, keep first.
        positions = sorted(set(positions), key=lambda x: x[1])
        sections: Dict[str, str] = {}
        for idx, (canonical, line_idx) in enumerate(positions):
            next_idx = positions[idx + 1][1] if idx + 1 < len(positions) else len(lines)
            sections[canonical] = "\n".join(lines[line_idx + 1 : next_idx]).strip()

        # Always add raw body if not present
        sections.setdefault("body", text)
        return sections

    def _guess_name(self, text: str) -> Optional[str]:
        # First non-empty line often holds the name
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            cleaned = re.sub(r"[|•·]", " ", cleaned)
            tokens = [t for t in cleaned.split() if t]
            if 1 < len(tokens) <= 5 and all(re.match(r"^[A-Z][a-zA-Z'.\-]+$", t) for t in tokens):
                return cleaned
            break
        return None

    def _find_email(self, text: str) -> Optional[str]:
        m = _EMAIL_RE.search(text)
        return m.group(0) if m else None

    def _find_phone(self, text: str) -> Optional[str]:
        m = _PHONE_RE.search(text)
        return m.group(0).strip() if m else None

    def _extract_skills(self, skills_section: str, full_text: str) -> List[str]:
        # Prefer explicit skills section; otherwise fall back to full-text scan
        corpus = skills_section if skills_section else full_text
        if not corpus:
            return []
        detected = detect_skills(corpus)
        if not detected and skills_section:
            detected = detect_skills(full_text)
        return detected

    def _extract_experience(self, section: str) -> List[Dict[str, Any]]:
        if not section:
            return []
        entries: List[Dict[str, Any]] = []
        current: Dict[str, Any] | None = None
        for line in section.splitlines():
            line = line.strip()
            if not line:
                continue
            # A header-like line followed by another line suggests a new entry
            if self._looks_like_role(line):
                if current:
                    entries.append(current)
                current = {"role": line, "details": []}
            else:
                if current is None:
                    current = {"role": None, "details": []}
                current["details"].append(line)
        if current:
            entries.append(current)

        # Try to attach years mentioned next to a role
        for entry in entries:
            text_blob = " ".join([entry.get("role") or ""] + entry.get("details", []))
            years_match = _YEARS_RE.search(text_blob)
            entry["years_estimate"] = (
                float(years_match.group(1)) if years_match else None
            )
        return entries

    def _extract_education(self, section: str) -> List[Dict[str, Any]]:
        if not section:
            return []
        entries: List[Dict[str, Any]] = []
        for line in section.splitlines():
            cleaned = line.strip(" -•|·")
            if not cleaned:
                continue
            entries.append({"description": cleaned})
        return entries

    def _extract_projects(self, section: str) -> List[Dict[str, Any]]:
        if not section:
            return []
        entries: List[Dict[str, Any]] = []
        for line in section.splitlines():
            cleaned = line.strip(" -•|·")
            if not cleaned:
                continue
            entries.append({"description": cleaned})
        return entries

    def _extract_certifications(self, section: str) -> List[str]:
        if not section:
            return []
        certs: List[str] = []
        for line in section.splitlines():
            cleaned = line.strip(" -•|·")
            if cleaned:
                certs.append(cleaned)
        return certs

    def _estimate_years(self, text: str) -> Optional[float]:
        match = _YEARS_RE.search(text)
        if match:
            return float(match.group(1))
        # Approximate based on date ranges (very rough)
        years = [int(y) for y in re.findall(r"\b(19|20)\d{2}\b", text)]
        if len(years) >= 2:
            span = max(years) - min(years)
            if 0 < span < 60:
                return float(span)
        return None

    def _looks_like_role(self, line: str) -> bool:
        # Heuristic: short uppercase or capitalized line, possibly with @ or dates
        if len(line) > 90:
            return False
        if re.search(r"\b(19|20)\d{2}\b", line):
            return True
        if "@" in line:
            return True
        words = line.split()
        if 1 < len(words) <= 12 and sum(1 for w in words if w[:1].isupper()) >= 2:
            return True
        return False


def parse_resume_from_file(path: Path) -> ResumeData:
    """Convenience helper: parse a resume from a file path."""
    text = path.read_text(errors="ignore")
    return ResumeParser().parse_text(text)
