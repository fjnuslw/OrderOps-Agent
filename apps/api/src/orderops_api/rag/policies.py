from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


POLICY_DIR = Path("data/policies")


@dataclass(frozen=True)
class PolicyDocument:
    doc_id: str
    version: str
    effective_date: str
    owner: str
    risk_level: str
    title: str
    body: str
    source_path: Path


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    doc_id: str
    section_id: str
    title: str
    text: str
    source_path: str
    risk_level: str


def load_policy_documents(policy_dir: Path = POLICY_DIR) -> list[PolicyDocument]:
    return [load_policy_document(path) for path in sorted(policy_dir.glob("*.md"))]


def load_policy_document(path: Path) -> PolicyDocument:
    text = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    title = first_markdown_heading(body) or metadata["doc_id"]
    return PolicyDocument(
        doc_id=metadata["doc_id"],
        version=metadata.get("version", ""),
        effective_date=metadata.get("effective_date", ""),
        owner=metadata.get("owner", ""),
        risk_level=metadata.get("risk_level", "medium"),
        title=title,
        body=body.strip(),
        source_path=path,
    )


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        raise ValueError("Policy document must start with YAML-style frontmatter.")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Policy document frontmatter is not closed.")

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    if "doc_id" not in metadata:
        raise ValueError("Policy document frontmatter must include doc_id.")

    return metadata, parts[2].strip()


def first_markdown_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def chunk_policy_document(document: PolicyDocument) -> list[PolicyChunk]:
    sections = split_markdown_sections(document.body)
    chunks: list[PolicyChunk] = []
    for index, (heading, section_text) in enumerate(sections, start=1):
        section_id = f"{document.doc_id}#s{index}"
        text = f"{document.title}\n{heading}\n{section_text}".strip()
        chunks.append(
            PolicyChunk(
                chunk_id=section_id,
                doc_id=document.doc_id,
                section_id=section_id,
                title=heading,
                text=text,
                source_path=str(document.source_path),
                risk_level=document.risk_level,
            )
        )
    return chunks


def split_markdown_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    current_heading = "Document"
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []

    for line in lines:
        if re.match(r"^##\s+", line):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line.lstrip("#").strip()
            current_lines = []
            continue
        if line.startswith("# "):
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(heading, body) for heading, body in sections if body]


def load_policy_chunks(policy_dir: Path = POLICY_DIR) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for document in load_policy_documents(policy_dir):
        chunks.extend(chunk_policy_document(document))
    return chunks
