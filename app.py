"""Online Voting System - Flask application.

Routes are grouped into public, voter and admin sections.
All SQL lives in models.py.
"""
import os
import re
import secrets
import time
from functools import wraps

from dotenv import load_dotenv

load_dotenv()

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from mysql.connector import Error, IntegrityError, errorcode
from werkzeug.security import check_password_hash, generate_password_hash

from models import AdminModel, CandidateModel, Database, UserModel, VoteModel

app = Flask(__name__)

# The secret key signs the session cookie, so it must come from the environment.
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy .env.example to .env and add a value."
    )
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # sessions last one hour

db = Database()
user_model = UserModel(db)
admin_model = AdminModel(db)
candidate_model = CandidateModel(db)
vote_model = VoteModel(db)

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,30}")
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


# ---------------------------------------------------------------------------
# Login protection: lock a client out for a while after repeated failures
# ---------------------------------------------------------------------------
class LoginLimiter:
    """Counts failed logins per client address (kept in memory)."""

    def __init__(self, max_attempts=5, lock_seconds=300):
        self.max_attempts = max_attempts
        self.lock_seconds = lock_seconds
        self.failures = {}  # key -> (failed_count, time_of_last_failure)

    def is_locked(self, key):
        entry = self.failures.get(key)
        if entry is None:
            return False
        count, last_time = entry
        if time.time() - last_time > self.lock_seconds:
            del self.failures[key]
            return False
        return count >= self.max_attempts

    def record_failure(self, key):
        entry = self.failures.get(key)
        count = 0
        if entry is not None and time.time() - entry[1] <= self.lock_seconds:
            count = entry[0]
        self.failures[key] = (count + 1, time.time())

    def reset(self, key):
        self.failures.pop(key, None)


login_limiter = LoginLimiter()


# ---------------------------------------------------------------------------
# CSRF protection: every POST form must send the token stored in the session
# ---------------------------------------------------------------------------
def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def check_csrf_token():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        saved = session.get("csrf_token", "")
        if not saved or not secrets.compare_digest(sent.encode(), saved.encode()):
            abort(400)


# ---------------------------------------------------------------------------
# Access control decorators
# ---------------------------------------------------------------------------
def login_required(view):
    """Allow the page only for a logged-in voter."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    """Allow the page only for a logged-in admin."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in as admin to continue.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped_view


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_registration(full_name, username, email, password, confirm_password):
    errors = []
    if not 2 <= len(full_name) <= 100:
        errors.append("Name must be between 2 and 100 characters.")
    if not USERNAME_PATTERN.fullmatch(username):
        errors.append(
            "Username must be 3 to 30 characters and can contain only "
            "letters, numbers and underscores."
        )
    if len(email) > 100 or not EMAIL_PATTERN.fullmatch(email):
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password != confirm_password:
        errors.append("Password and confirm password do not match.")
    return errors


def read_candidate_form():
    """Read and validate the add/edit candidate form."""
    form = {
        "name": request.form.get("name", "").strip(),
        "party": request.form.get("party", "").strip(),
        "description": request.form.get("description", "").strip(),
    }
    errors = []
    if not 2 <= len(form["name"]) <= 100:
        errors.append("Candidate name must be between 2 and 100 characters.")
    if len(form["party"]) > 100:
        errors.append("Party name can have at most 100 characters.")
    if len(form["description"]) > 500:
        errors.append("Description can have at most 500 characters.")
    return form, errors


def client_key(kind):
    return kind + ":" + str(request.remote_addr)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    form = {}
    if request.method == "POST":
        form = {
            "full_name": request.form.get("full_name", "").strip(),
            "username": request.form.get("username", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
        }
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = validate_registration(
            form["full_name"], form["username"], form["email"],
            password, confirm_password,
        )

        if not errors:
            for row in user_model.find_duplicates(form["username"], form["email"]):
                if row["username"].lower() == form["username"].lower():
                    errors.append("That username is already taken.")
                if row["email"].lower() == form["email"]:
                    errors.append("That email is already registered.")
            errors = list(dict.fromkeys(errors))  # remove repeated messages

        if not errors:
            try:
                user_model.create(
                    form["full_name"], form["username"], form["email"],
                    generate_password_hash(password),
                )
            except IntegrityError as error:
                # Two people registering at the same moment can still collide.
                if error.errno == errorcode.ER_DUP_ENTRY:
                    errors.append("That username or email is already registered.")
                else:
                    raise
            else:
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))

        for message in errors:
            flash(message, "error")

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        key = client_key("user")
        if login_limiter.is_locked(key):
            flash("Too many failed attempts. Please try again in a few minutes.", "error")
            return render_template("login.html")

        login_name = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = user_model.find_by_login(login_name) if login_name else None

        if user and check_password_hash(user["password_hash"], password):
            login_limiter.reset(key)
            session.clear()  # start a fresh session after login
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))

        login_limiter.record_failure(key)
        flash("Invalid username/email or password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Voter routes
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = user_model.find_by_id(session["user_id"])
    if user is None:  # account no longer exists
        session.clear()
        flash("Please log in again.", "error")
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        user=user,
        vote=vote_model.get_vote(user["id"]),
        candidate_count=candidate_model.count(),
    )


@app.route("/candidates")
@login_required
def candidate_list():
    return render_template(
        "candidates.html",
        candidates=candidate_model.get_all(),
        vote=vote_model.get_vote(session["user_id"]),
    )


@app.route("/vote", methods=["GET", "POST"])
@login_required
def vote():
    user_id = session["user_id"]
    existing_vote = vote_model.get_vote(user_id)

    if request.method == "POST":
        # Server-side check: the form is ignored if this voter already voted.
        if existing_vote:
            flash("You have already voted. Each voter can vote only once.", "error")
            return redirect(url_for("dashboard"))

        candidate_id = request.form.get("candidate_id", type=int)
        candidate = candidate_model.find(candidate_id) if candidate_id else None
        if candidate is None:
            flash("Please select a valid candidate.", "error")
            return redirect(url_for("vote"))

        try:
            vote_model.cast(user_id, candidate["id"])
        except IntegrityError as error:
            # The UNIQUE key on votes.user_id blocks a second vote in the database.
            if error.errno == errorcode.ER_DUP_ENTRY:
                flash("You have already voted. Each voter can vote only once.", "error")
                return redirect(url_for("dashboard"))
            raise

        flash("Your vote has been recorded. Thank you for voting.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "vote.html", vote=existing_vote, candidates=candidate_model.get_all()
    )


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        key = client_key("admin")
        if login_limiter.is_locked(key):
            flash("Too many failed attempts. Please try again in a few minutes.", "error")
            return render_template("admin_login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = admin_model.find_by_username(username) if username else None

        if admin and check_password_hash(admin["password_hash"], password):
            login_limiter.reset(key)
            session.clear()
            session.permanent = True
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            flash("Admin logged in successfully.", "success")
            return redirect(url_for("admin_dashboard"))

        login_limiter.record_failure(key)
        flash("Invalid admin username or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    flash("Admin logged out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        total_voters=user_model.count(),
        total_votes=vote_model.count(),
        total_candidates=candidate_model.count(),
    )


@app.route("/admin/candidates")
@admin_required
def admin_candidates():
    return render_template("admin_candidates.html", candidates=candidate_model.get_all())


@app.route("/admin/candidates/add", methods=["GET", "POST"])
@admin_required
def admin_add_candidate():
    form = {"name": "", "party": "", "description": ""}
    if request.method == "POST":
        form, errors = read_candidate_form()
        if not errors:
            try:
                candidate_model.create(form["name"], form["party"], form["description"])
            except IntegrityError as error:
                if error.errno == errorcode.ER_DUP_ENTRY:
                    errors.append("A candidate with this name already exists.")
                else:
                    raise
            else:
                flash("Candidate added.", "success")
                return redirect(url_for("admin_candidates"))
        for message in errors:
            flash(message, "error")

    return render_template(
        "admin_candidate_form.html",
        form=form,
        heading="Add Candidate",
        form_action=url_for("admin_add_candidate"),
    )


@app.route("/admin/candidates/edit/<int:candidate_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_candidate(candidate_id):
    candidate = candidate_model.find(candidate_id)
    if candidate is None:
        flash("Candidate not found.", "error")
        return redirect(url_for("admin_candidates"))

    form = {
        "name": candidate["name"],
        "party": candidate["party"],
        "description": candidate["description"],
    }
    if request.method == "POST":
        form, errors = read_candidate_form()
        if not errors:
            try:
                candidate_model.update(
                    candidate_id, form["name"], form["party"], form["description"]
                )
            except IntegrityError as error:
                if error.errno == errorcode.ER_DUP_ENTRY:
                    errors.append("A candidate with this name already exists.")
                else:
                    raise
            else:
                flash("Candidate updated.", "success")
                return redirect(url_for("admin_candidates"))
        for message in errors:
            flash(message, "error")

    return render_template(
        "admin_candidate_form.html",
        form=form,
        heading="Edit Candidate",
        form_action=url_for("admin_edit_candidate", candidate_id=candidate_id),
    )


@app.route("/admin/candidates/delete/<int:candidate_id>", methods=["POST"])
@admin_required
def admin_delete_candidate(candidate_id):
    if candidate_model.find(candidate_id) is None:
        flash("Candidate not found.", "error")
        return redirect(url_for("admin_candidates"))

    try:
        candidate_model.delete(candidate_id)
    except IntegrityError as error:
        # The foreign key refuses to delete a candidate who already has votes.
        if error.errno == errorcode.ER_ROW_IS_REFERENCED_2:
            flash("This candidate already has votes and cannot be deleted.", "error")
            return redirect(url_for("admin_candidates"))
        raise

    flash("Candidate deleted.", "success")
    return redirect(url_for("admin_candidates"))


@app.route("/admin/results")
@admin_required
def admin_results():
    total_votes = vote_model.count()
    total_voters = user_model.count()

    results = []
    for row in vote_model.results():
        percent = round(row["vote_count"] * 100 / total_votes, 1) if total_votes else 0
        results.append({**row, "percent": percent})

    return render_template(
        "results.html",
        results=results,
        total_votes=total_votes,
        total_voters=total_voters,
        not_voted=total_voters - total_votes,
    )


# ---------------------------------------------------------------------------
# Error pages: users see a short message, details go to the server log
# ---------------------------------------------------------------------------
def error_page(title, message, status):
    return render_template("error.html", title=title, message=message), status


@app.errorhandler(400)
def bad_request(error):
    return error_page("Invalid Request", "The form was invalid or has expired. Please go back and try again.", 400)


@app.errorhandler(404)
def not_found(error):
    return error_page("Page Not Found", "The page you are looking for does not exist.", 404)


@app.errorhandler(405)
def method_not_allowed(error):
    return error_page("Not Allowed", "This action is not allowed for this page.", 405)


@app.errorhandler(500)
def server_error(error):
    return error_page("Something Went Wrong", "An unexpected error occurred. Please try again later.", 500)


@app.errorhandler(Error)
def database_error(error):
    app.logger.error("Database error: %s", error)
    return error_page("Database Problem", "The system could not complete your request right now. Please try again later.", 500)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
