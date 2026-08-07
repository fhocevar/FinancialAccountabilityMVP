import json
import re
import subprocess
from pathlib import Path
from typing import Any
import sys
import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    USE_OLLAMA,
    WHISPER_COMMAND,
)
from .models import Client


class ExtractedCommitment(BaseModel):
    client_name: str = "Unknown"
    description: str
    owner: str = "Unassigned"
    due_date: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str


def transcribe_audio(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(
            f"Audio file not found: {path}"
        )

    command = [
        sys.executable,
        "-m",
        "scripts.transcribe",
        str(path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=Path(__file__).resolve().parent.parent,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "Whisper transcription failed"
        )

    transcript = result.stdout.strip()

    if not transcript:
        raise RuntimeError(
            "Whisper returned an empty transcript"
        )

    return transcript


def _rules(text: str) -> list[dict[str, Any]]:
    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )
        if sentence.strip()
    ]

    result: list[dict[str, Any]] = []

    current_client = "Unknown"
    current_owner = "Unassigned"

    for index, sentence in enumerate(sentences):
        client_match = re.search(
            r"(?:client|cliente)\s+"
            r"([A-Z][\w'-]+"
            r"(?:\s+[A-Z][\w'-]+){1,3})",
            sentence,
            re.I,
        )

        if client_match:
            current_client = (
                client_match
                .group(1)
                .strip()
                .rstrip(",.")
            )

        owner_match = re.search(
            r"\b([A-Z][a-z]+)\s+"
            r"(?:will|is going to|vai|ficará|fica)\s+"
            r"(?:handle|send|call|take care|responsável|cuidar)",
            sentence,
        )

        if owner_match:
            current_owner = owner_match.group(1)

        is_commitment = re.search(
            r"\b("
            r"need to|must|will|should|"
            r"precisamos|deve|vou|"
            r"enviar|ligar|send|call|follow up"
            r")\b",
            sentence,
            re.I,
        )

        if not is_commitment:
            continue

        owner = current_owner

        next_sentence = (
            sentences[index + 1]
            if index + 1 < len(sentences)
            else ""
        )

        next_owner_match = re.search(
            r"\b([A-Z][a-z]+)\s+will\s+"
            r"(?:handle|send|call|take care)",
            next_sentence,
        )

        if next_owner_match:
            owner = next_owner_match.group(1)

        description = re.sub(
            r"^(?:about|regarding)\s+"
            r"(?:client\s+)?[^,]+,\s*",
            "",
            sentence,
            flags=re.I,
        ).strip()

        evidence = sentence

        if (
            next_owner_match
            and next_sentence
        ):
            evidence = (
                f"{sentence} {next_sentence}"
            )

        result.append(
            {
                "client_name": current_client,
                "description": description,
                "owner": owner,
                "due_date": None,
                "confidence": 0.72,
                "evidence": evidence,
            }
        )

    return result


def _build_prompt(text: str) -> str:
    return f"""
You are an information extraction engine for a regulated
financial-services accountability system.

Your task is to identify explicit commitments, tasks, follow-ups,
or promises contained in the transcript.

Return ONLY valid JSON.

Required structure:

{{
  "commitments": [
    {{
      "client_name": "string",
      "description": "short actionable description",
      "owner": "string",
      "due_date": null,
      "confidence": 0.0,
      "evidence": "exact supporting text from transcript"
    }}
  ]
}}

Rules:

1. Do not invent information.
2. Use context across adjacent sentences.
3. If a later sentence assigns an owner to the previous task,
   associate that owner with the task.
4. If the client is unknown, use "Unknown".
5. If the owner is unknown, use "Unassigned".
6. If there is no explicit due date, use null.
7. confidence must be between 0.0 and 1.0.
8. evidence must be copied from the transcript, not paraphrased.
9. description should contain only the actionable commitment,
   not unnecessary introductory text.
10. Do not create a commitment for general discussion,
    observations, status updates, or completed actions unless
    they clearly represent a new task.
11. Return an empty commitments array if there are no commitments.

Transcript:

{text}
""".strip()


def _extract_with_ollama(
    text: str,
) -> list[dict[str, Any]]:
    prompt = _build_prompt(text)

    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        },
        timeout=180,
    )

    response.raise_for_status()

    payload = response.json()

    raw_response = payload.get("response")

    if not raw_response:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    parsed = json.loads(raw_response)

    if isinstance(parsed, list):
        raw_items = parsed

    elif isinstance(parsed, dict):
        raw_items = parsed.get(
            "commitments",
            [],
        )

    else:
        raise ValueError(
            "Unexpected Ollama JSON structure."
        )

    if not isinstance(raw_items, list):
        raise ValueError(
            "'commitments' must be a JSON array."
        )

    validated: list[dict[str, Any]] = []

    for raw_item in raw_items:
        try:
            item = ExtractedCommitment.model_validate(
                raw_item
            )
        except ValidationError:
            continue

        client_name = (
            item.client_name.strip()
            or "Unknown"
        )

        owner = (
            item.owner.strip()
            or "Unassigned"
        )

        description = (
            item.description.strip()
        )

        evidence = (
            item.evidence.strip()
        )

        if not description:
            continue

        if not evidence:
            continue

        # Não aceita evidência inventada.
        if evidence.lower() not in text.lower():
            continue

        validated.append(
            {
                "client_name": client_name,
                "description": description,
                "owner": owner,
                "due_date": item.due_date,
                "confidence": item.confidence,
                "evidence": evidence,
            }
        )

    return validated


def extract_commitments(
    text: str,
) -> list[dict[str, Any]]:
    normalized_text = text.strip()

    if not normalized_text:
        return []

    if USE_OLLAMA:
        try:
            ollama_result = _extract_with_ollama(
                normalized_text
            )

            if ollama_result:
                return ollama_result

        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValidationError,
            ValueError,
            RuntimeError,
            TimeoutError,
        ) as exc:
            print(
                "[OLLAMA FALLBACK] "
                f"{type(exc).__name__}: {exc}"
            )

        except Exception as exc:
            print(
                "[OLLAMA FALLBACK - UNEXPECTED] "
                f"{type(exc).__name__}: {exc}"
            )

    return _rules(normalized_text)


def resolve_client(
    db: Session,
    name: str,
) -> Client:
    normalized_name = (
        name or "Unknown"
    ).strip()

    if not normalized_name:
        normalized_name = "Unknown"

    client = db.scalar(
        select(Client).where(
            Client.name.ilike(
                normalized_name
            )
        )
    )

    if client:
        return client

    client = Client(
        name=normalized_name,
    )

    db.add(client)
    db.flush()

    return client