"""Optional faster-whisper wrapper. Install faster-whisper separately."""
import sys
from faster_whisper import WhisperModel
if len(sys.argv)!=2: raise SystemExit("usage: transcribe.py AUDIO")
model=WhisperModel("small",device="cpu",compute_type="int8")
segments,_=model.transcribe(sys.argv[1],vad_filter=True)
print(" ".join(s.text.strip() for s in segments))
