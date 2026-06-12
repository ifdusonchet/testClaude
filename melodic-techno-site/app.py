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

# Image filenames live in static/images/gear/.
# Set GEAR_BANNER_IMAGE to "studio-setup.jpg" (or any name) once the photo is ready.
# Set each category's "image" to "moogs.jpg" etc. to activate the photo.
GEAR_BANNER_IMAGE = None

GEAR_CATEGORIES = [
    {
        "id": "brain",
        "number": "01",
        "title": "The Brain",
        "tagline": "Akai Force",
        "image": None,   # e.g. "brain.jpg"
        "intro": None,
        "instruments": [
            {
                "name": "Akai Force",
                "role": "The Conductor",
                "description": (
                    "At the centre of my setup sits the Akai Force: the conductor of this electronic orchestra.\n\n"
                    "It is far more than a sampler. It is my drum machine, MIDI sequencer, performance hub, and "
                    "creative sketchbook. Every riff begins with human hands on real instruments. I play melodies "
                    "and basslines live on each synthesizer, capturing the MIDI notes in the Force so they can be "
                    "replayed while I continue shaping the sound directly from the hardware.\n\n"
                    "This allows me to focus on what I love most: opening filters, twisting knobs, adding movement "
                    "and imperfections, and letting each machine reveal its personality in real time.\n\n"
                    "The Akai Force is also remarkably flexible. Through MIDI and USB, it connects and synchronises "
                    "more than twenty synthesizers and drum machines, keeping the entire setup breathing together as "
                    "one living instrument.\n\n"
                    "In many ways, it is the brain of the studio: remembering what has been played, coordinating "
                    "every voice, and leaving my hands free to transform performance into something spontaneous and alive."
                ),
            },
        ],
        "outro": None,
    },
    {
        "id": "moogs",
        "number": "02",
        "title": "The Moogs",
        "tagline": "Soul, Muscle, and Madness",
        "image": None,   # e.g. "moogs.jpg"
        "intro": "If the Akai Force is the brain of the setup, the Moogs are undoubtedly its soul.",
        "instruments": [
            {
                "name": "Moog Subsequent 37",
                "role": "The Charmer",
                "description": (
                    "The Subsequent 37 has earned its reputation as one of the most iconic bass machines ever built, "
                    "and deservedly so. Its low end is thick, warm, and impossible to ignore. But reducing it to a "
                    "bass synthesizer misses half of its personality.\n\n"
                    "Beyond the growling basslines lies an extraordinary lead instrument. With its expressive "
                    "modulation possibilities and evolving movements, it can sing, whisper, or scream. There is "
                    "something unmistakably \"Moog\" about its sound. Even in the busiest mix, the Subsequent 37 "
                    "somehow finds a way to make itself heard."
                ),
            },
            {
                "name": "Moog Minitaur",
                "role": "The Pocket Giant",
                "description": (
                    "The Minitaur is often introduced as a dedicated bass synth. That's true — but only if you "
                    "lack imagination.\n\n"
                    "Hidden behind its compact chassis is a remarkably expressive instrument. Its two oscillators, "
                    "envelopes, and LFO allow it to produce far more than earth-shaking lows. It excels at simple "
                    "yet unforgettable melodies that carry a surprising emotional weight.\n\n"
                    "Built like a tank and barely larger than a pair of hands, the Minitaur has become one of my "
                    "most faithful companions. It travels with me to every live performance, proving that greatness "
                    "doesn't always require a large footprint."
                ),
            },
            {
                "name": "Moog Matriarch",
                "role": "The Queen",
                "description": (
                    "Part synthesizer, part instrument of chaos, part work of art.\n\n"
                    "A four-note paraphonic, semi-modular monster, the Matriarch refuses the comfort of certainty. "
                    "There are no presets to save. Every patch exists only in the moment it is created. Every sound "
                    "is temporary. Every performance becomes unique.\n\n"
                    "It demands your full attention and rewards experimentation with textures and colours unlike "
                    "anything else in my studio. Its sound is vast, organic, and alive. Once the Matriarch enters "
                    "a mix, it rarely settles into the background. It becomes part of the track's identity.\n\n"
                    "Many synthesizers strive for perfection. The Matriarch strives for character. And for that "
                    "reason, it remains one of the most inspiring instruments I have ever played."
                ),
            },
        ],
        "outro": None,
    },
    {
        "id": "dreadbox",
        "number": "03",
        "title": "The Greek Gang",
        "tagline": "Dreadbox",
        "image": None,   # e.g. "greek-gang.jpg"
        "intro": (
            "If the Moogs are refined storytellers, the Dreadbox machines are wild poets.\n\n"
            "Built in Greece and entirely analogue, these synthesizers are simpler than their American cousins. "
            "They offer less control, fewer safety nets, and little interest in behaving properly. Their oscillators "
            "drift. Their resonance screams. Their imperfections refuse to be corrected.\n\n"
            "And that is precisely why I love them. They don't whisper, \"Listen to me.\" They shout, \"We exist!\""
        ),
        "instruments": [
            {
                "name": "Dreadbox Erebus V2",
                "role": "The Beast",
                "description": (
                    "The Erebus V2 is simplicity itself: two oscillators, a handful of classic waveforms, a creamy "
                    "analogue filter, and a wonderfully unstable analogue delay. On paper, it shouldn't be extraordinary.\n\n"
                    "In reality, it shakes walls.\n\n"
                    "Its bass can rattle the furniture, and when its filter begins to cry, even the neighbours become "
                    "unwilling participants in the performance. There is something primal about the Erebus V2. "
                    "It doesn't strive for sophistication. It aims directly for your instincts."
                ),
            },
            {
                "name": "Dreadbox Erebus V3",
                "role": "The Mad Scientist",
                "description": (
                    "The Erebus V3 takes everything its older brother does and asks: what happens if we push things further?\n\n"
                    "A third oscillator enters the picture, capable of acting as an additional LFO. Ring modulation "
                    "and cross-modulation open the doors to stranger territories, while frequency modulation introduces "
                    "metallic textures and unexpected harmonics.\n\n"
                    "The V2 is raw power. The V3 is experimentation. It invites accidents, rewards curiosity, and "
                    "constantly tempts you to turn one knob too far just to discover what lies beyond."
                ),
            },
            {
                "name": "Dreadbox Typhon",
                "role": "The Dream Painter",
                "description": (
                    "The smallest member of the family, yet perhaps the most surprising.\n\n"
                    "Unlike the Erebus siblings, the Typhon isn't obsessed with brute force. Its two analogue "
                    "oscillators remain wonderfully alive, but they surrender part of their control to simplicity. "
                    "You don't sculpt every detail. Instead, you collaborate with the machine and let it guide you "
                    "toward places you hadn't planned to visit.\n\n"
                    "And then come the effects. Its extraordinary digital effects engine transforms sounds into "
                    "landscapes. Delays dissolve into mist, reverbs stretch beyond the horizon, and modulation "
                    "paints movement and colour onto every note.\n\n"
                    "The Erebus machines scream. The Typhon dreams. Sometimes, listening to it feels less like "
                    "hearing a synthesizer and more like standing in front of an Impressionist painting — where "
                    "details disappear, emotions take over, and what matters most is not what you see, but what you feel."
                ),
            },
        ],
        "outro": None,
    },
    {
        "id": "wavetable",
        "number": "04",
        "title": "The Dream Weavers",
        "tagline": "Wavetable Synthesis",
        "image": None,   # e.g. "dream-weavers.jpg"
        "intro": (
            "If analogue synthesizers are made of electricity and instinct, wavetable synthesizers are built from possibility.\n\n"
            "They bring a modern touch to the studio. Less concerned with recreating the past, they constantly ask "
            "what sound could become next. Their landscapes evolve, morph, and shimmer. They can imitate reality, "
            "but they truly come alive when they create something that has never existed before."
        ),
        "instruments": [
            {
                "name": "ASM Hydrasynth",
                "role": "The Explorer",
                "description": (
                    "Some synthesizers hide their power behind endless menus. The Hydrasynth does the opposite.\n\n"
                    "It may be one of the deepest instruments in my studio, yet somehow it remains one of the easiest "
                    "to understand. Its workflow invites experimentation. One idea naturally leads to another. Complex "
                    "modulation becomes intuitive, and happy accidents happen constantly.\n\n"
                    "It feels less like programming a machine and more like exploring an unknown world with an excellent "
                    "map in your hands. Every time I sit in front of it, I discover a new path I had somehow missed before."
                ),
            },
            {
                "name": "Modal Argon8",
                "role": "The Poet",
                "description": (
                    "The first thing you notice is the keyboard. It is simply magnificent. Responsive, expressive, "
                    "and inviting — it makes you want to play long after the sound has faded away. And fortunately, "
                    "the sound itself lives up to the touch.\n\n"
                    "The Argon8 has a unique elegance. Its wavetable engine produces tones that feel polished without "
                    "losing warmth. It excels at pads that breathe, evolving textures, and melodies that seem "
                    "suspended in mid-air.\n\n"
                    "If the Hydrasynth is the explorer, the Argon8 is the poet. It reminds you that technology can still be graceful."
                ),
            },
            {
                "name": "Waldorf Iridium Core",
                "role": "The Alchemist",
                "description": (
                    "Some synthesizers specialise. The Iridium refuses.\n\n"
                    "Wavetable synthesis. Granular. Sampling. Virtual analogue. Resonators. It is less an instrument "
                    "and more a laboratory for sound. The possibilities are almost overwhelming.\n\n"
                    "It can become nearly anything you imagine, but it asks something in return: patience, curiosity, "
                    "and the willingness to lose yourself for hours while searching for a sound that has never existed "
                    "before. This is not a synthesizer for shortcuts. It is a creation machine."
                ),
            },
            {
                "name": "Novation Peak",
                "role": "The Gentleman",
                "description": (
                    "I love all my synthesizers. But the Peak occupies a special place in my heart.\n\n"
                    "It combines the richness and unpredictability that I adore in analogue instruments with the "
                    "flexibility of modern digital design. Almost one knob per function — no fighting with menus, "
                    "no interruption between inspiration and creation.\n\n"
                    "And then there is the reverb. It doesn't simply place sounds into a space. It sings. Pads bloom "
                    "into cathedrals, leads float above the mix, and simple notes suddenly acquire emotion. Elegant "
                    "without losing its soul.\n\n"
                    "If I had to choose one synthesizer outside of my beloved Moogs, this might be the one."
                ),
            },
            {
                "name": "Roland Gaia 2",
                "role": "The Hidden Treasure",
                "description": (
                    "The Gaia 2 is often underestimated. At first glance, it seems simple. Approachable. Almost modest.\n\n"
                    "But spend time with it and another personality slowly emerges. Beneath its friendly surface lies "
                    "an instrument capable of surprising complexity. Wavetables sit beside virtual analogue engines. "
                    "Modulations create movement and life. Familiar sounds evolve into unexpected textures.\n\n"
                    "The Gaia never demands attention. Instead, it quietly whispers: \"Have you tried this?\" "
                    "And before long, an hour has disappeared. Sometimes the most rewarding instruments are the ones "
                    "that gently invite you to keep discovering."
                ),
            },
        ],
        "outro": None,
    },
    {
        "id": "korg",
        "number": "05",
        "title": "The Korg Tribe",
        "tagline": "The Shape-Shifters",
        "image": None,   # e.g. "korg-tribe.jpg"
        "intro": (
            "Some instruments find their voice and remain faithful to it for decades. "
            "The Korg tribe prefers transformation.\n\n"
            "These synthesizers are restless creatures. They evolve, mutate, and challenge the idea that an "
            "instrument should have a single identity. They ask questions rather than provide answers: what if "
            "a sequence could become a landscape? What if FM synthesis could finally become musical instead of mathematical?"
        ),
        "instruments": [
            {
                "name": "Korg Wavestate",
                "role": "The Storyteller",
                "description": (
                    "The Wavestate doesn't simply play notes. It tells stories.\n\n"
                    "Built around the idea of wave sequencing, it constantly rearranges itself. Samples evolve, "
                    "rhythms shift, textures drift in and out of focus. A patch is never truly static. It breathes.\n\n"
                    "Press a key and what begins as a piano may become a choir, then dissolve into percussion before "
                    "returning as something entirely unexpected. The Wavestate rewards patience and imagination. "
                    "Sometimes cinematic. Sometimes nostalgic. Always moving."
                ),
            },
            {
                "name": "Korg Modwave",
                "role": "The Surfer",
                "description": (
                    "The Modwave takes the world of wavetables and injects it with pure energy.\n\n"
                    "If the Wavestate tells stories, the Modwave rides waves. Its sounds twist and morph "
                    "continuously, moving between aggression and beauty with astonishing ease. It excels at modern "
                    "textures, evolving leads, and animated timbres that never seem to settle in one place.\n\n"
                    "Push it gently and it shimmers. Push it harder and it becomes wild. "
                    "The Modwave reminds me that movement itself can be musical."
                ),
            },
            {
                "name": "Korg Opsix",
                "role": "The Translator",
                "description": (
                    "For decades, FM synthesis had a reputation: powerful, complex, unforgiving. "
                    "The Opsix changes that story.\n\n"
                    "It takes one of the most intimidating forms of synthesis ever created and translates it into "
                    "something human. Suddenly, bells, electric pianos, metallic textures, crystalline pads, and "
                    "impossible harmonics become invitations rather than puzzles.\n\n"
                    "There is still enormous depth beneath the surface, but the fear is gone. The Opsix proves "
                    "that complexity does not have to be complicated. Sometimes all it takes is the right guide "
                    "to reveal the beauty hidden behind mathematics."
                ),
            },
        ],
        "outro": (
            "Together, the Korg tribe reminds me that music is never fixed.\n\n"
            "A melody can become a rhythm. A rhythm can become a texture. A texture can become an emotion. "
            "Everything can transform into something else.\n\n"
            "And perhaps that is what creativity truly is: not inventing from nothing, but discovering "
            "what something else could become."
        ),
    },
    {
        "id": "outlaws",
        "number": "06",
        "title": "The Outlaws",
        "tagline": "The Ones Who Refused to Behave",
        "image": None,   # e.g. "outlaws.jpg"
        "intro": (
            "Every orchestra has its virtuosos. Every family has its black sheep. These are mine.\n\n"
            "The synthesizers that don't quite belong anywhere else. The rebels, the innovators, the strange "
            "little machines built by dreamers who decided that the established rules of synthesis were merely suggestions.\n\n"
            "Sometimes they are brilliant. Sometimes they are infuriating. They are never boring."
        ),
        "instruments": [
            {
                "name": "Norand Mono",
                "role": "The French Revolutionary",
                "description": (
                    "This was my very first synthesizer. My gateway drug.\n\n"
                    "Born from French imagination, the Norand Mono answered an ambitious question: what if a modern "
                    "synthesizer could offer deep modulation without screens, menus, or endless scrolling?\n\n"
                    "The answer was elegance. Every knob is surrounded by LEDs that quietly tell you where you stand. "
                    "Everything remains immediate, tactile, alive.\n\n"
                    "At first glance, it almost resembles a Roland TB-303: compact, simple, approachable. Don't be "
                    "fooled. Behind that minimalist interface hides a monster of modulation. It taught me that the "
                    "deepest instruments don't always look complicated."
                ),
            },
            {
                "name": "The Handmade Beast",
                "role": "When Only Sound Matters",
                "description": (
                    "At some point, practicality gave way to obsession.\n\n"
                    "Inside a Moog enclosure, I assembled an unlikely creature: a Dreadbox Hades living side by "
                    "side with a Behringer Brain. No concern for appearances. No concern for conventions. Only sound.\n\n"
                    "And what a sound it is. Aggressive, metallic, unapologetic. Less synthesizer. "
                    "More electric guitar forged from voltage. It doesn't ask for refinement. It demands attitude."
                ),
            },
            {
                "name": "Behringer Edge",
                "role": "The Primitive Force",
                "description": (
                    "Do not try to control it.\n\n"
                    "The Edge has its own agenda. It grooves. It pulses. It spits out rhythms that feel older than "
                    "melody itself. Primitive and hypnotic, it doesn't politely wait for instructions.\n\n"
                    "Instead, it presents an idea and dares you to build an entire track around it. "
                    "Fight it, and you lose. Dance with it, and suddenly everything falls into place. "
                    "This is techno in its purest form."
                ),
            },
            {
                "name": "Arturia MicroFreak & MiniFreak",
                "role": "The Mad Inventors",
                "description": (
                    "If there is a glimpse of the future hidden in my studio, these two might be it.\n\n"
                    "Unlike almost anything else, they don't expose every parameter and don't pretend to satisfy "
                    "the purists. Instead, they ask a simple question: what do you want to hear?\n\n"
                    "Granular textures. Virtual analogue warmth. Speech-like articulations. Metallic chaos. "
                    "Delicate pads. They borrow the most inspiring ideas from the modular world and make them "
                    "accessible without requiring a wall full of patch cables. Curious. Creative. Playful."
                ),
            },
            {
                "name": "East Beast & West Pest",
                "role": "The Brothers at War",
                "description": (
                    "These two little semi-modular twins tell the entire story of synthesizer history.\n\n"
                    "The East Beast follows the East Coast philosophy: oscillators, filters, subtraction. Sculpting "
                    "sound by removing frequencies until what remains feels right.\n\n"
                    "The West Pest walks another path. Wavefolders. Complex harmonics. Addition and transformation. "
                    "Rather than carving away, it encourages sound to evolve into stranger and stranger forms.\n\n"
                    "Two philosophies. Two brothers. One eternal argument. But feeding the Moog Matriarch through "
                    "the West Pest's wavefolder opens doors to textures neither instrument could discover alone. "
                    "Sometimes the most beautiful sounds emerge not from choosing sides, but from letting opposites collaborate."
                ),
            },
        ],
        "outro": (
            "And perhaps that is the true lesson of this entire studio.\n\n"
            "Analogue and digital. Precision and chaos. Tradition and innovation. East and West.\n\n"
            "None of them are enemies. Music begins when they learn to speak to one another."
        ),
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
    return render_template("gear.html", gear_categories=GEAR_CATEGORIES, gear_banner=GEAR_BANNER_IMAGE)


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
