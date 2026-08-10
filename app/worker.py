import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal
from .models import AuditEvent, Commitment, Meeting
from .services import (
    extract_commitments,
    resolve_client,
    transcribe_audio,
)


POLL_INTERVAL_SECONDS = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def audit(
    db,
    meeting: Meeting,
    event_type: str,
    details: str = "",
) -> None:
    db.add(
        AuditEvent(
            user_id=meeting.created_by_id,
            event_type=event_type,
            actor="worker",
            details=details,
        )
    )


def process_meeting(meeting_id: int) -> None:
    with SessionLocal() as db:
        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if not meeting:
            print(
                f"[WORKER] Meeting {meeting_id} not found."
            )
            return

        if meeting.processing_status != "QUEUED":
            return

        started_at = utc_now()

        try:
            meeting.processing_started_at = started_at
            meeting.processing_finished_at = None
            meeting.processing_seconds = None
            meeting.processing_error = None

            audit(
                db,
                meeting,
                "MEETING_PROCESSING_STARTED",
                f"Meeting {meeting.id}",
            )

            db.commit()

            #
            # TRANSCRIPTION
            #
            if meeting.source_type == "AUDIO":
                meeting.processing_status = "TRANSCRIBING"

                audit(
                    db,
                    meeting,
                    "MEETING_TRANSCRIBING",
                    meeting.original_filename or "",
                )

                db.commit()

                if not meeting.stored_file_path:
                    raise RuntimeError(
                        "Audio meeting does not have stored_file_path"
                    )

                audio_path = Path(
                    meeting.stored_file_path
                )

                if not audio_path.exists():
                    raise RuntimeError(
                        f"Audio file not found: {audio_path}"
                    )

                transcript = transcribe_audio(
                    audio_path
                ).strip()

                if not transcript:
                    raise RuntimeError(
                        "Whisper returned an empty transcript."
                    )

                meeting.transcript = transcript

                db.commit()

            #
            # EXTRACTION
            #
            meeting.processing_status = "EXTRACTING"

            audit(
                db,
                meeting,
                "MEETING_EXTRACTING",
                f"Model extraction started for meeting {meeting.id}",
            )

            db.commit()

            text = (
                meeting.transcript
                or ""
            ).strip()

            if not text:
                raise RuntimeError(
                    "Meeting transcript is empty."
                )

            extracted_items = extract_commitments(
                text
            )

            #
            # REMOVE PREVIOUS COMMITMENTS
            #
            existing = list(
                db.scalars(
                    select(Commitment).where(
                        Commitment.meeting_id
                        == meeting.id
                    )
                )
            )

            for item in existing:
                db.delete(item)

            db.flush()

            #
            # CREATE COMMITMENTS
            #
            for extracted in extracted_items:
                client = resolve_client(
                    db,
                    extracted.get(
                        "client_name",
                        "Unknown",
                    ),
                )

                commitment = Commitment(
                    meeting_id=meeting.id,
                    client_id=client.id,
                    client_name=client.name,
                    description=(
                        extracted.get("description")
                        or extracted.get("evidence")
                        or ""
                    ),
                    owner=(
                        extracted.get("owner")
                        or "Unassigned"
                    ),
                    due_date=extracted.get(
                        "due_date"
                    ),
                    confidence=float(
                        extracted.get(
                            "confidence",
                            0.5,
                        )
                    ),
                    evidence=(
                        extracted.get("evidence")
                        or ""
                    ),
                )

                db.add(commitment)
                db.flush()

                db.add(
                    AuditEvent(
                        commitment_id=commitment.id,
                        user_id=meeting.created_by_id,
                        event_type="COMMITMENT_EXTRACTED",
                        actor="worker",
                        details=commitment.evidence,
                    )
                )

            #
            # FINISH PROCESSING
            #
            finished_at = utc_now()

            meeting.processing_status = (
                "PENDING_REVIEW"
                if extracted_items
                else "COMPLETED"
            )

            meeting.processing_finished_at = (
                finished_at
            )

            meeting.processing_seconds = (
                finished_at - started_at
            ).total_seconds()

            audit(
                db,
                meeting,
                "MEETING_PROCESSING_COMPLETED",
                (
                    f"{len(extracted_items)} commitments; "
                    f"{meeting.processing_seconds:.2f}s"
                ),
            )

            db.commit()

            print(
                f"[WORKER] Meeting {meeting.id} "
                f"processed successfully: "
                f"{len(extracted_items)} commitments "
                f"in {meeting.processing_seconds:.2f}s"
            )

        except Exception as exc:
            db.rollback()

            meeting = db.get(
                Meeting,
                meeting_id,
            )

            if meeting:
                finished_at = utc_now()

                meeting.processing_status = "FAILED"

                meeting.processing_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                meeting.processing_finished_at = (
                    finished_at
                )

                if meeting.processing_started_at:
                    meeting.processing_seconds = (
                        finished_at
                        - meeting.processing_started_at
                    ).total_seconds()

                audit(
                    db,
                    meeting,
                    "MEETING_PROCESSING_FAILED",
                    meeting.processing_error,
                )

                db.commit()

            print(
                f"[WORKER] Meeting {meeting_id} failed: "
                f"{type(exc).__name__}: {exc}"
            )


def get_next_meeting() -> int | None:
    with SessionLocal() as db:
        meeting = db.scalar(
            select(Meeting)
            .where(
                Meeting.processing_status
                == "QUEUED"
            )
            .order_by(
                Meeting.created_at
            )
            .limit(1)
        )

        if not meeting:
            return None

        return meeting.id


def main() -> None:
    print(
        "[WORKER] Financial Accountability worker started."
    )

    while True:
        meeting_id = get_next_meeting()

        if meeting_id is None:
            time.sleep(
                POLL_INTERVAL_SECONDS
            )
            continue

        process_meeting(
            meeting_id
        )


if __name__ == "__main__":
    main()