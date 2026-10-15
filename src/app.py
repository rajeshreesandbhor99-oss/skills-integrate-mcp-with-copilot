"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import json
import os
import secrets
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHER_CREDENTIALS_FILE = Path(os.getenv(
    "TEACHER_CREDENTIALS_FILE", current_dir / "teachers.json"
))
SESSION_COOKIE = "teacher_session"
SESSION_LIFETIME_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
sessions: dict[str, tuple[str, float]] = {}


class TeacherLogin(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


def load_teacher_credentials() -> list[dict[str, str]]:
    try:
        with TEACHER_CREDENTIALS_FILE.open(encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured. Set up the teacher credentials file.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail="The teacher credentials file contains invalid JSON.",
        ) from error

    if not isinstance(credentials, list):
        raise HTTPException(
            status_code=500,
            detail="The teacher credentials file must contain a JSON list.",
        )

    usernames = set()
    for entry in credentials:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("username"), str)
            or not entry["username"]
            or not isinstance(entry.get("password_hash"), str)
        ):
            raise HTTPException(
                status_code=500,
                detail="The teacher credentials file has an invalid entry.",
            )
        if entry["username"] in usernames:
            raise HTTPException(
                status_code=500,
                detail="The teacher credentials file contains duplicate usernames.",
            )
        usernames.add(entry["username"])
        _parse_password_hash(entry["password_hash"])

    return credentials


def _parse_password_hash(password_hash: str) -> tuple[int, bytes, bytes]:
    try:
        algorithm, iterations, salt, expected_hash = password_hash.split("$")
        iteration_count = int(iterations)
        salt_bytes = bytes.fromhex(salt)
        expected_bytes = bytes.fromhex(expected_hash)
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail="The teacher credentials file contains an invalid password hash.",
        ) from error

    if (
        algorithm != "pbkdf2_sha256"
        or not 100_000 <= iteration_count <= 2_000_000
        or len(salt_bytes) < 16
        or len(expected_bytes) != hashlib.sha256().digest_size
    ):
        raise HTTPException(
            status_code=500,
            detail="The teacher credentials file contains an invalid password hash.",
        )
    return iteration_count, salt_bytes, expected_bytes


def verify_password(password: str, password_hash: str) -> bool:
    iterations, salt, expected_hash = _parse_password_hash(password_hash)
    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return secrets.compare_digest(actual_hash, expected_hash)


def get_teacher_session(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    now = time.monotonic()
    expired_tokens = [
        session_token
        for session_token, (_, expires_at) in sessions.items()
        if expires_at <= now
    ]
    for expired_token in expired_tokens:
        del sessions[expired_token]

    if token is None or token not in sessions:
        return None
    return sessions[token][0]


def require_teacher(request: Request) -> str:
    username = get_teacher_session(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_current_teacher(request: Request):
    username = get_teacher_session(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: TeacherLogin, response: Response):
    teacher_credentials = load_teacher_credentials()
    teacher = next(
        (
            entry
            for entry in teacher_credentials
            if entry["username"] == credentials.username
        ),
        None,
    )
    if teacher is None:
        salt = bytes.fromhex("0" * 32)
        expected_hash = bytes.fromhex("0" * 64)
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            credentials.password.encode("utf-8"),
            salt,
            PASSWORD_HASH_ITERATIONS,
        )
        secrets.compare_digest(actual_hash, expected_hash)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(credentials.password, teacher["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = (
        teacher["username"],
        time.monotonic() + SESSION_LIFETIME_SECONDS,
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "username": teacher["username"]}


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        sessions.pop(token, None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
