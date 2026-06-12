"""
app.py — Main Flask application for the melodic techno artist site.

To run locally:
    pip install -r requirements.txt
    cp .env.example .env   # then fill in your values
    python app.py
"""

import os
import csv
import io
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, make_response, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import database as db
import email_sender
import pdf_generator

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Expose config values to all Jinja2 templates
app.config["SITE_NAME"] = os.environ.get("SITE_NAME", "TheFAB")

# Hash the admin password once at startup so we never store it in plain text
_raw_admin_pw = os.environ.get("ADMIN_PASSWORD", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(_raw_admin_pw)


# ── Bootstrap the database on every startup ───────────────────
db.init_db()

# ── Pre-generate recipe PDFs so they're ready to download ─────
# (called after the recipes data is defined below)


# ══════════════════════════════════════════════════════════════
# CONTENT DATA
# Edit these dicts to update the site without touching templates.
# ══════════════════════════════════════════════════════════════

GEAR = [
    {
        "category": "Synthesizer",
        "name": "Moog Subsequent 37",
        "description": (
            "The backbone of the low end. Its ladder filter produces the "
            "dark, resonant bass that defines the sound — warm yet menacing, "
            "capable of the deep sub-rumble that melodic techno demands."
        ),
        "image": None,
    },
    {
        "category": "Synthesizer",
        "name": "Roland Jupiter-Xm",
        "description": (
            "Handles the layered pad textures and wide, atmospheric chords. "
            "The classic Roland sound engine gives an unmistakable "
            "analogue warmth to evolving chord progressions."
        ),
        "image": None,
    },
    {
        "category": "Drum Machine",
        "name": "Roland TR-8S",
        "description": (
            "The rhythmic engine. Punchy kicks with long tails, crisp "
            "hi-hats and that classic analogue snare crack. "
            "Pattern-based workflow keeps everything spontaneous and alive."
        ),
        "image": None,
    },
    {
        "category": "Drum Machine",
        "name": "Elektron Digitakt",
        "description": (
            "Sample sequencer and MIDI brain. Used to trigger synths, "
            "sequence breaks and add field-recorded textures that blur "
            "the line between electronic and organic."
        ),
        "image": None,
    },
    {
        "category": "Effects",
        "name": "Strymon BigSky",
        "description": (
            "Reverb that turns a single piano note into a vast cavernous "
            "space. The 'Hall' and 'Bloom' algorithms are in constant use — "
            "they are the source of the signature atmospheric depth."
        ),
        "image": None,
    },
    {
        "category": "Software",
        "name": "Ableton Live 12",
        "description": (
            "Recording, arrangement and mixing hub. Hardware runs into "
            "Ableton via audio interface; the DAW is used for arrangement "
            "and subtle processing, not as a composition crutch."
        ),
        "image": None,
    },
]

TRACKS = [
    {
        "title": "Matriarche Requiem",
        "original_artist": "Original composition",
        "original_song": "Moog Matriarch · vocal laments",
        "process": (
            "A heartbeat echoes through the darkness, steady and inevitable. "
            "Around it, the Moog Matriarch breathes and growls, weaving mournful "
            "melodies that feel both human and machine. Male and female voices rise "
            "like distant laments, answering one another in a timeless complaint — "
            "part prayer, part farewell. Matriarche Requiem is a descent into the "
            "shadows, where grief becomes rhythm and sorrow finds its place on the dancefloor."
        ),
        "bpm": 130,
        "youtube_id": "2KziErGS114",
        "tags": ["melodic", "dark", "vocal"],
    },
    {
        "title": "Jeunesse lève-toi !",
        "original_artist": "Damien Saez",
        "original_song": "Jeunesse lève-toi",
        "process": (
            "Born from the fire and poetry of Damien Saez's words, Jeunesse lève-toi ! "
            "is a call to those who refuse resignation. It speaks to the restless hearts "
            "that still believe the world can be changed, that cynicism is not destiny, "
            "and that hope is an act of courage. Driven by the energy of techno and "
            "carried by the urgency of its message, this track is an invitation to rise, "
            "to dream, and to leave a mark brighter than indifference."
        ),
        "bpm": 133,
        "youtube_id": "aQ1P0CQlaAY",
        "tags": ["melodic", "anthem", "vocal"],
    },
    {
        "title": "Tee",
        "original_artist": "Lomepal",
        "original_song": "Tee",
        "process": (
            "Inspired by Lomepal's lyrics, Tee captures the vertigo of losing control "
            "of your own trajectory. Like a golf ball balanced on its tee, there is that "
            "suspended moment before impact: fragile, exposed, powerless. You know the hit "
            "is coming, but not where it will send you. Carried by tense rhythms and an "
            "underlying sense of urgency, the track explores the chaos of being pushed by "
            "forces stronger than yourself, while desperately trying to remain whole."
        ),
        "bpm": 127,
        "youtube_id": "0rTbk9IGEsk",
        "tags": ["melodic", "hypnotic", "french"],
    },
    {
        "title": "Revolution",
        "original_artist": "Multi-source collage",
        "original_song": "Fragments of multiple songs",
        "process": (
            "A collision of voices, rhythms, and memories, Revolution blends fragments "
            "of different songs into a relentless drum and bass journey. Tribal percussion "
            "drives the pulse forward, raw and instinctive, while the lyrics echo a single "
            "message: the world does not change through silence. Energetic and untamed, "
            "this track is less a song than a gathering cry — an invitation to move, to "
            "resist, and to remember that every revolution begins with a heartbeat shared by many."
        ),
        "bpm": 135,
        "youtube_id": "xa_eD1TCdOw",
        "tags": ["drum & bass", "tribal", "political"],
    },
    {
        "title": "Wicked Game",
        "original_artist": "Chris Isaak",
        "original_song": "Wicked Game",
        "process": (
            "Inspired by the haunting lyrics of Chris Isaak's Wicked Game, this track "
            "explores the irresistible pull of an impossible love. It is the story of "
            "knowing the danger and stepping closer anyway — of a fragile creature drawn "
            "to something infinitely more powerful than itself. Like a rabbit falling in "
            "love with a T-Rex, it is beautiful, absurd, tender, and doomed from the very "
            "beginning. Wrapped in melancholic melodies and hypnotic rhythms, Wicked Game "
            "dances in that thin space where desire overrules reason and the heart willingly "
            "enters a battle it cannot win."
        ),
        "bpm": 125,
        "youtube_id": "le0Taj6TVeQ",
        "tags": ["melodic", "melancholic", "cinematic"],
    },
]

RECIPES = [
    {
        "name": "Slow-Braised Lamb Shoulder",
        "description": (
            "Seven hours in the oven, pulled apart with two forks. "
            "Built on a base of anchovies, garlic and rosemary — "
            "flavours that disappear into the meat and become something else entirely."
        ),
        "key_ingredients": ["Lamb shoulder", "Anchovies", "Rosemary", "Garlic", "Red wine"],
        "ingredients": [
            "1 bone-in lamb shoulder (~2 kg)",
            "6 anchovy fillets in oil",
            "1 whole head of garlic, cloves separated and peeled",
            "4 sprigs fresh rosemary",
            "250 ml red wine",
            "400 ml lamb or chicken stock",
            "2 tbsp olive oil",
            "Salt and black pepper",
        ],
        "steps": [
            "Preheat oven to 160°C (fan 140°C).",
            "Score the lamb all over with a small knife. Push an anchovy fillet and a garlic clove into each cut.",
            "Season generously with salt and pepper. Lay rosemary sprigs over the top.",
            "Heat olive oil in a large flameproof casserole over high heat. Sear the lamb on all sides until deep brown, about 3 minutes per side.",
            "Pour in the wine and let it bubble for 1 minute, then add the stock.",
            "Cover tightly with a lid or foil. Transfer to the oven.",
            "Braise for 6–7 hours until the meat falls away from the bone at the lightest touch.",
            "Rest uncovered for 20 minutes before pulling. Reduce the braising liquid on the hob to make a sauce.",
        ],
        "filename": "slow-braised-lamb-shoulder",
    },
    {
        "name": "Pasta al Limone",
        "description": (
            "Five ingredients. Ten minutes. One of the most satisfying pasta dishes "
            "in existence. The lemon must be unwaxed — everything depends on the zest."
        ),
        "key_ingredients": ["Spaghetti", "Lemon", "Parmesan", "Butter", "Black pepper"],
        "ingredients": [
            "400 g spaghetti or linguine",
            "2 unwaxed lemons — zest of both, juice of one",
            "80 g unsalted butter, cold and cubed",
            "80 g Parmigiano Reggiano, finely grated",
            "Generous amount of freshly cracked black pepper",
            "Salt for pasta water",
        ],
        "steps": [
            "Cook pasta in heavily salted boiling water until 1 minute before al dente. Reserve 2 cups of pasta water.",
            "In a wide pan over medium-low heat, melt half the butter with the lemon zest. Toast gently for 30 seconds.",
            "Add the lemon juice and 1 cup of pasta water. Bring to a gentle simmer.",
            "Add the drained pasta and toss constantly, adding cold butter cubes one at a time.",
            "Add Parmesan gradually, tossing and adding splashes of pasta water to maintain a silky sauce.",
            "Remove from heat. Add a very generous amount of black pepper. Toss once more and serve immediately.",
        ],
        "filename": "pasta-al-limone",
    },
    {
        "name": "Dark Chocolate & Espresso Tart",
        "description": (
            "A tart that belongs on the same playlist as the music. "
            "Bittersweet, dense, barely sweet. The espresso deepens the chocolate "
            "without announcing itself."
        ),
        "key_ingredients": ["Dark chocolate (70%)", "Espresso", "Double cream", "Eggs", "Butter"],
        "ingredients": [
            "For the crust: 200 g plain flour, 100 g cold butter, 30 g icing sugar, 1 egg yolk, 2 tbsp cold water",
            "For the filling: 250 g dark chocolate (70%), 200 ml double cream, 60 ml strong espresso, 2 eggs, 1 egg yolk, 30 g caster sugar, pinch of salt",
        ],
        "steps": [
            "Make the crust: pulse flour, butter and sugar in a food processor until it resembles breadcrumbs. Add egg yolk and water; bring together. Chill 30 minutes.",
            "Roll out and line a 23 cm tart tin. Prick the base and blind-bake at 180°C for 15 minutes, remove weights, bake 5 more minutes until golden.",
            "Melt chocolate and cream together over a bain-marie until smooth. Remove from heat.",
            "Stir in the espresso and salt. Let cool to room temperature.",
            "Whisk eggs, egg yolk and sugar until combined; stir gently into the chocolate mixture.",
            "Pour into the cooled tart shell. Bake at 160°C for 18–20 minutes — the centre should still wobble slightly.",
            "Cool completely at room temperature, then chill 2 hours before slicing.",
        ],
        "filename": "dark-chocolate-espresso-tart",
    },
    {
        "name": "Roasted Bone Marrow on Toast",
        "description": (
            "Arguably the most satisfying thing you can eat in under 30 minutes. "
            "Elemental. Rich. Best eaten standing up with a glass of something cold."
        ),
        "key_ingredients": ["Beef marrow bones", "Sourdough", "Parsley", "Capers", "Lemon"],
        "ingredients": [
            "4 beef marrow bones, cut crosswise (~8 cm sections)",
            "4 thick slices of good sourdough",
            "Small handful of flat-leaf parsley, roughly chopped",
            "1 tbsp capers, drained and roughly chopped",
            "1 small shallot, very finely diced",
            "Juice of half a lemon",
            "Good flaky sea salt",
            "Olive oil",
        ],
        "steps": [
            "Preheat oven to 230°C. Stand the bones upright on a baking tray.",
            "Roast for 15–20 minutes until the marrow is soft, starting to bubble and pull away from the bone.",
            "While the bones roast, mix parsley, capers, shallot and lemon juice with a little olive oil. Season.",
            "Toast the sourdough until deeply golden.",
            "Scoop the marrow straight onto the toast. Add a generous pinch of flaky salt.",
            "Top with the parsley-caper salad and eat immediately.",
        ],
        "filename": "roasted-bone-marrow",
    },
]

DOWNLOADS = {
    "Sound Packs": [
        {"name": "Dark Pads Vol. 1", "meta": "WAV · 48 samples · 180 MB", "icon": "🎛️", "file": None},
        {"name": "Moog Bass Textures", "meta": "WAV · 32 samples · 95 MB", "icon": "🎛️", "file": None},
        {"name": "Atmospheric Foley", "meta": "WAV · 64 samples · 240 MB", "icon": "🎛️", "file": None},
    ],
    "MIDI Files": [
        {"name": "Requiem in 128 — Full Arrangement", "meta": "MIDI · 4 tracks", "icon": "🎹", "file": None},
        {"name": "Intermezzo — Main Melody", "meta": "MIDI · 1 track", "icon": "🎹", "file": None},
        {"name": "Chord Progressions Pack", "meta": "MIDI · 12 patterns", "icon": "🎹", "file": None},
    ],
    "Synth Presets": [
        {"name": "Moog Subsequent 37 — Dark Basses", "meta": "Sysex · 24 presets", "icon": "🔊", "file": None},
        {"name": "Jupiter-Xm — Pad Landscapes", "meta": "Tone file · 16 presets", "icon": "🔊", "file": None},
    ],
    "Recipes (PDF)": [],  # populated dynamically below
}


def _ensure_recipe_pdfs():
    """Generate PDFs for all recipes if they don't already exist."""
    for recipe in RECIPES:
        path = os.path.join(
            os.path.dirname(__file__),
            "static", "downloads", "recipes",
            recipe["filename"] + ".pdf",
        )
        if not os.path.exists(path):
            pdf_generator.generate_recipe_pdf(recipe)

        DOWNLOADS["Recipes (PDF)"].append({
            "name": recipe["name"],
            "meta": "PDF · Recipe card",
            "icon": "📄",
            "file": f"downloads/recipes/{recipe['filename']}.pdf",
        })


_ensure_recipe_pdfs()


# ══════════════════════════════════════════════════════════════
# AUTH HELPERS
# ══════════════════════════════════════════════════════════════

def admin_required(f):
    """Decorator: redirect to admin login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def get_download_token():
    """Return the download access token from the request cookie, or None."""
    return request.cookies.get("dl_token")


def has_download_access():
    token = get_download_token()
    if not token:
        return False
    return db.get_subscriber_by_token(token) is not None


# ══════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def home():
    # Show the first track as the featured track on the home page
    featured = TRACKS[0] if TRACKS else None
    return render_template("home.html", featured=featured)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/gear")
def gear():
    return render_template("gear.html", gear=GEAR)


@app.route("/music")
def music():
    return render_template("music.html", tracks=TRACKS)


@app.route("/cooking")
def cooking():
    return render_template("cooking.html", recipes=RECIPES)


@app.route("/downloads", methods=["GET", "POST"])
def downloads():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("downloads"))

        token = db.add_subscriber(email)
        flash("You're in! Enjoy the downloads.", "success")

        response = make_response(redirect(url_for("downloads")))
        # Cookie lasts one year
        response.set_cookie("dl_token", token, max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax")
        return response

    if has_download_access():
        return render_template("downloads.html", downloads=DOWNLOADS)

    return render_template("downloads_gate.html")


@app.route("/static/downloads/recipes/<path:filename>")
def serve_recipe_pdf(filename):
    """Serve recipe PDFs only to visitors with download access."""
    if not has_download_access():
        return redirect(url_for("downloads"))
    directory = os.path.join(app.root_path, "static", "downloads", "recipes")
    return send_from_directory(directory, filename, as_attachment=True)


# ══════════════════════════════════════════════════════════════
# ADMIN ROUTES  (not linked in navigation)
# ══════════════════════════════════════════════════════════════

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect password.", "error")

    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    subscribers = db.get_all_subscribers()
    email_logs  = db.get_email_logs()
    count       = db.subscriber_count()
    return render_template(
        "admin/dashboard.html",
        subscribers=subscribers,
        email_logs=email_logs,
        subscriber_count=count,
    )


@app.route("/admin/export-csv")
@admin_required
def admin_export_csv():
    """Download all subscriber emails as a CSV file."""
    subscribers = db.get_all_subscribers()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "email", "joined"])
    for sub in subscribers:
        writer.writerow([sub["id"], sub["email"], sub["created_at"]])

    csv_data = output.getvalue()
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=subscribers.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@app.route("/admin/send-email", methods=["POST"])
@admin_required
def admin_send_email():
    """Send a newsletter to all subscribers."""
    subject = request.form.get("subject", "").strip()
    body    = request.form.get("body", "").strip()

    if not subject or not body:
        flash("Subject and body are both required.", "error")
        return redirect(url_for("admin_dashboard"))

    recipients = db.get_subscriber_emails()
    success, message = email_sender.send_newsletter(subject, body, recipients)

    if success:
        db.log_email_send(subject, body, len(recipients))
        flash(f"Email sent. {message}", "success")
    else:
        flash(f"Send failed: {message}", "error")

    return redirect(url_for("admin_dashboard"))


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # debug=True gives auto-reload during development.
    # Set debug=False (or remove this file's __main__ block) in production.
    app.run(debug=True, port=5000)
