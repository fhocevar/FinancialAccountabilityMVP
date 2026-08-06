import json, re, subprocess, tempfile
from pathlib import Path
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import OLLAMA_MODEL, OLLAMA_URL, USE_OLLAMA, WHISPER_COMMAND
from .models import Client

def transcribe_audio(path: Path) -> str:
    if not WHISPER_COMMAND:
        raise RuntimeError("Whisper is not configured. Set WHISPER_COMMAND or paste a transcript.")
    out = subprocess.run([*WHISPER_COMMAND.split(), str(path)], capture_output=True, text=True, timeout=1800)
    if out.returncode != 0: raise RuntimeError(out.stderr.strip() or "Whisper command failed")
    return out.stdout.strip()

def _rules(text: str):
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    result=[]; current_client="Unknown"; current_owner="Unassigned"
    for i,s in enumerate(sentences):
        cm=re.search(r"(?:client|cliente)\s+([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){1,3})", s, re.I)
        if cm: current_client=cm.group(1).strip().rstrip(",.")
        om=re.search(r"\b([A-Z][a-z]+)\s+(?:will|is going to|vai|ficará|fica)\s+(?:handle|send|call|take care|responsável|cuidar)", s)
        if om: current_owner=om.group(1)
        prev = sentences[i-1] if i else ""
        if re.search(r"\b(need to|must|will|should|precisamos|deve|vou|enviar|ligar|send|call|follow up)\b", s, re.I):
            owner=current_owner
            next_s=sentences[i+1] if i+1<len(sentences) else ""
            nom=re.search(r"\b([A-Z][a-z]+)\s+will\s+(?:handle|send|call|take care)", next_s)
            if nom: owner=nom.group(1)
            desc=re.sub(r"^(?:about|regarding)\s+(?:client\s+)?[^,]+,\s*", "", s, flags=re.I)
            result.append({"client_name":current_client,"description":desc,"owner":owner,"due_date":None,"confidence":.72,"evidence":s})
    return result

def extract_commitments(text: str):
    if USE_OLLAMA:
        prompt='''Extract commitments from the transcript. Return ONLY a JSON array with client_name, description, owner, due_date, confidence, evidence. Do not invent. Transcript:\n'''+text
        try:
            r=httpx.post(f"{OLLAMA_URL}/api/generate",json={"model":OLLAMA_MODEL,"prompt":prompt,"stream":False,"format":"json"},timeout=120)
            r.raise_for_status(); data=json.loads(r.json()["response"])
            if isinstance(data,dict): data=data.get("commitments",[])
            if isinstance(data,list): return data
        except Exception: pass
    return _rules(text)

def resolve_client(db: Session, name: str):
    name=(name or "Unknown").strip()
    client=db.scalar(select(Client).where(Client.name.ilike(name)))
    if not client:
        client=Client(name=name); db.add(client); db.flush()
    return client
