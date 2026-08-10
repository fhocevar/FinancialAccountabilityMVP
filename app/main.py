from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .config import APP_NAME, BASE_DIR, SECRET_KEY, UPLOAD_DIR
from .database import SessionLocal, get_db
from .models import AuditEvent, Client, Commitment, Meeting, User
from .security import (current_user,hash_password,require_roles,verify_password,)
from .services import extract_commitments, resolve_client, transcribe_audio


app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="financial_accountability_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "app" / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "app" / "templates",
)


def get_session_user(request: Request) -> User | None:
    """
    Recupera o usuário autenticado diretamente da sessão.

    Dessa forma não dependemos de um segundo middleware.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    with SessionLocal() as db:
        return db.get(User, user_id)


def render(
    request: Request,
    name: str,
    **context,
):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "app_name": APP_NAME,
            "user": get_session_user(request),
            **context,
        },
    )

@app.on_event("startup")
def seed_admin():
    with SessionLocal() as db:
        if not db.scalar(select(User).limit(1)):
            db.add(User(name="Administrator", email="admin@local", password_hash=hash_password("Admin123!"), role="ADMIN"))
            db.commit()

def require(request: Request, db: Session):
    return current_user(request, db)

def aging_bucket(c: Commitment):
    if c.status != "OPEN": return "CLOSED"
    days = max(0, (datetime.now(timezone.utc).replace(tzinfo=None) - c.created_at).days)
    return "GREEN" if days <= 7 else "YELLOW" if days <= 21 else "RED"

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    return render(
        request,
        "login.html",
        error=None,
    )

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return render(request, "login.html", error="Invalid credentials")
    request.session["user_id"] = user.id
    return RedirectResponse("/", 303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    require(request, db)
    commitments = list(db.scalars(select(Commitment).order_by(Commitment.created_at.desc())))
    rows = [{"item": c, "bucket": aging_bucket(c)} for c in commitments]
    counts = {x: 0 for x in ["GREEN", "YELLOW", "RED", "CLOSED"]}
    for row in rows: counts[row["bucket"]] += 1
    return render(request, "dashboard.html", rows=rows, counts=counts)

@app.get("/meetings", response_class=HTMLResponse)
def meetings_page(
    request: Request,
    db: Session = Depends(get_db),
):
    require_roles(
        request,
        db,
        "MANAGER",
        "ADVISOR",
        "REVIEWER",
    )

    meetings = list(
        db.scalars(
            select(Meeting).order_by(
                Meeting.created_at.desc()
            )
        )
    )

    return render(
        request,
        "meetings.html",
        meetings=meetings,
    )

@app.post("/meetings")
async def create_meeting(
    request: Request,
    title: str = Form(...),
    meeting_date: str = Form(...),
    transcript: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = require_roles(
        request,
        db,
        "MANAGER",
        "ADVISOR",
    )

    text = transcript.strip()
    filename = None
    source = "TEXT"
    stored_file_path = None

    if file and file.filename:

        filename = Path(
            file.filename
        ).name

        path = (
            UPLOAD_DIR
            / (
                f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_"
                f"{filename}"
            )
        )

        path.write_bytes(
            await file.read()
        )

        stored_file_path = str(
            path.resolve()
        )

        audio_extensions = {
            ".mp3",
            ".wav",
            ".m4a",
            ".mp4",
            ".ogg",
            ".webm",
        }

        if path.suffix.lower() in audio_extensions:
            source = "AUDIO"
            text = ""

        else:
            source = "FILE"

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()

    if (
        source != "AUDIO"
        and not text
    ):
        raise HTTPException(
            status_code=400,
            detail="Transcript or audio file is required",
        )

    meeting = Meeting(
        title=title.strip(),
        meeting_date=meeting_date,
        transcript=text,
        source_type=source,
        original_filename=filename,
        stored_file_path=stored_file_path,
        processing_status="QUEUED",
        created_by_id=user.id,
    )

    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return RedirectResponse(
        url=f"/meetings/{meeting.id}",
        status_code=303,
    )

@app.get("/meetings/{meeting_id}", response_class=HTMLResponse)
def meeting_detail(meeting_id: int, request: Request, db: Session = Depends(get_db)):
    require_roles(
    request,
    db,
    "MANAGER",
    "ADVISOR",
    "REVIEWER",
)
    meeting = db.get(Meeting, meeting_id)
    if not meeting: raise HTTPException(404, "Meeting not found")
    return render(request, "meeting_detail.html", meeting=meeting)

@app.get("/clients", response_class=HTMLResponse)
def clients_page(
    request: Request,
    db: Session = Depends(get_db),
):
    require_roles(
        request,
        db,
        "MANAGER",
        "ADVISOR",
        "REVIEWER",
        "AUDITOR",
    )

    clients = list(
        db.scalars(
            select(Client).order_by(
                Client.name
            )
        )
    )

    return render(
        request,
        "clients.html",
        clients=clients,
    )

@app.get("/clients/{client_id}", response_class=HTMLResponse)
def client_detail(client_id: int, request: Request, db: Session = Depends(get_db)):
    require_roles(
    request,
    db,
    "MANAGER",
    "ADVISOR",
    "REVIEWER",
    "AUDITOR",
)
    client = db.get(Client, client_id)
    if not client: raise HTTPException(404, "Client not found")
    return render(request, "client_detail.html", client=client)

@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request, db: Session = Depends(get_db)):
    require_roles(
        request,
        db,
        "MANAGER",
        "REVIEWER",
    )
    items = list(db.scalars(select(Commitment).where(Commitment.review_status == "PENDING_REVIEW").order_by(Commitment.created_at)))
    return render(request, "review.html", items=items)

@app.post("/commitments/{commitment_id}/review")
def review_commitment(commitment_id: int, request: Request, client_name: str = Form(...), description: str = Form(...), owner: str = Form(...), due_date: str = Form(""), action: str = Form(...), db: Session = Depends(get_db)):
    user = require_roles(
    request,
    db,
    "MANAGER",
    "REVIEWER",
)
    item = db.get(Commitment, commitment_id)
    if not item: raise HTTPException(404, "Commitment not found")
    before = f"{item.client_name}|{item.description}|{item.owner}|{item.review_status}"
    if action == "approve":
        client = resolve_client(db, client_name)
        item.client_id, item.client_name, item.description = client.id, client.name, description.strip()
        item.owner, item.due_date, item.review_status = owner.strip() or "Unassigned", due_date.strip() or None, "APPROVED"
        event = "COMMITMENT_APPROVED"
    elif action == "reject":
        item.review_status, item.status, event = "REJECTED", "CANCELLED", "COMMITMENT_REJECTED"
    else: raise HTTPException(400, "Invalid action")
    after = f"{item.client_name}|{item.description}|{item.owner}|{item.review_status}"
    db.add(AuditEvent(commitment_id=item.id, user_id=user.id, event_type=event, actor=user.email, before_json=before, after_json=after)); db.commit()
    return RedirectResponse("/review", 303)

@app.post("/commitments/{commitment_id}/close")
def close_commitment(commitment_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_roles(
    request,
    db,
    "MANAGER",
); item = db.get(Commitment, commitment_id)
    if not item: raise HTTPException(404, "Commitment not found")
    item.status, item.closed_at = "CLOSED", datetime.utcnow()
    db.add(AuditEvent(commitment_id=item.id, user_id=user.id, event_type="COMMITMENT_CLOSED", actor=user.email)); db.commit()
    return RedirectResponse("/", 303)

@app.post("/commitments/{commitment_id}/reopen")
def reopen_commitment(
    commitment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_roles(
        request,
        db,
        "MANAGER",
    )

    item = db.get(Commitment, commitment_id)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Commitment not found",
        )

    item.status = "OPEN"
    item.closed_at = None

    db.add(
        AuditEvent(
            commitment_id=item.id,
            user_id=user.id,
            event_type="COMMITMENT_REOPENED",
            actor=user.email,
        )
    )

    db.commit()

    return RedirectResponse(
        url="/",
        status_code=303,
    )

@app.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    db: Session = Depends(get_db),
):
    require_roles(
        request,
        db,
        "MANAGER",
        "AUDITOR",
    )

    events = list(
        db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.created_at.desc())
            .limit(500)
        )
    )

    return render(
        request,
        "audit.html",
        events=events,
    )
