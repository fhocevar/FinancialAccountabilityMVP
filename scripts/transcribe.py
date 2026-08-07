"""
Local Whisper transcription used by Financial Accountability MVP.
"""

import sys
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> None:

    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.transcribe <audio_file>",
            file=sys.stderr,
        )
        raise SystemExit(2)

    audio = Path(sys.argv[1]).resolve()

    if not audio.exists():
        print(
            f"Audio file not found: {audio}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",
    )

    segments, info = model.transcribe(
    str(audio),
    language="en",
    beam_size=5,
    vad_filter=True,
    initial_prompt=(
        "Financial services meeting. "
        "Common terms include annuity, insurance carrier, "
        "retirement account, beneficiary, contract, advisor, "
        "client, forms, review, follow-up. "
        "Possible names include Robert Smith, Susan, John, "
        "Mary Johnson, Michael Brown, Sarah."
    ),
)

    transcript = []

    for segment in segments:
        text = segment.text.strip()

        if text:
            transcript.append(text)

    result = " ".join(transcript).strip()

    if not result:
        print(
            "Whisper returned an empty transcript.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(result)


if __name__ == "__main__":
    main()