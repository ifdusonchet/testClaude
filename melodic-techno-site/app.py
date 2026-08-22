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
import hmac
import hashlib
import time
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

# Gear page narrative sections.
# Set "image" to a filename in static/images/gear/ once photos are ready.

STUDIO_SECTION = {
    "title": "Built on Curiosity",
    "image": "studio-setup.png",
    "text": (
        "People often ask me if I had a master plan when building this studio.\n\n"
        "The answer is simple:\n\n"
        "Absolutely not.\n\n"
        "There was no spreadsheet, no five-year strategy, no dream shopping list pinned to the wall. "
        "This studio was built piece by piece, one late-night discovery at a time. I spent countless "
        "hours browsing second-hand websites, music forums, and classified ads, waiting for a machine "
        "to catch my eye and spark that familiar feeling of excitement.\n\n"
        "Sometimes it was the sound.\n\n"
        "Sometimes the design.\n\n"
        "Sometimes simply the promise that it could teach me something new.\n\n"
        "If a synthesizer made me curious enough to imagine the music we could create together, "
        "it found its way into the studio.\n\n"
        "Over the years, those chance encounters grew into the collection you see today.\n\n"
        "At the centre of everything sits the Akai Force, placed directly in front of me like the "
        "captain at the helm of a ship. Around it live the instruments I return to most often: "
        "the Moogs, the Dreadbox machines, the companions whose controls have become second nature to my hands.\n\n"
        "The rest of the family waits patiently on a rack to my right.\n\n"
        "A glance away.\n\n"
        "Ready whenever inspiration decides to take an unexpected turn.\n\n"
        "This studio isn't a museum built to impress.\n\n"
        "It's a living workspace. A playground. A laboratory of happy accidents.\n\n"
        "Every instrument here earned its place by making me feel something."
    ),
}

LIVE_SET_SECTION = {
    "title": "Reducing an Orchestra to Its Essence",
    "image": "Live-set.jpg",
    # text_lead: the opening question — 4 short paragraphs with left blue accent line
    "text_lead": (
        "There is, of course, one practical problem with building an orchestra of more than twenty synthesizers:\n\n"
        "You can't fit it into the back of a car.\n\n"
        "So every live performance begins with the same question:\n\n"
        "\"If I could only bring the essentials, what would they be?\""
    ),
    # text_outro: the answer + poetic closing — rendered as a gear-instr-style card
    "text_outro": (
        "Packed inside a single flight case is my travelling studio: an Akai MPC One, a Dreadbox Erebus, "
        "the faithful Moog Minitaur, and two additional compact synthesizers chosen according to the mood of the set.\n\n"
        "The MPC One becomes the conductor.\n\n"
        "It sends MIDI sequences to the instruments travelling with me, allowing them to perform live while I "
        "shape the sounds in real time — opening filters, adding resonance, introducing movement, and responding "
        "to the energy of the audience.\n\n"
        "The voices that stay behind in the studio aren't forgotten. Their parts are carefully recorded as audio "
        "tracks inside the MPC, preserving the textures and atmospheres that helped shape each piece.\n\n"
        "The result sits somewhere between preparation and improvisation.\n\n"
        "Some machines speak directly from the stage.\n\n"
        "Others return as memories captured in sound.\n\n"
        "But there is never a simple press of a play button.\n\n"
        "Every performance evolves. Knobs are turned. Mistakes happen. Unexpected moments appear and disappear forever.\n\n"
        "The tracks breathe differently each night.\n\n"
        "Because behind all these machines, there is still a human being trying to transform electricity into emotion — "
        "and inviting a room full of strangers to share in the experience."
    ),
}

# Set each category's "image" to a filename (e.g. "moogs.jpg") to activate it.
GEAR_CATEGORIES = [
    {
        "id": "brain",
        "number": "01",
        "title": "The Brain",
        "tagline": "Akai Force",
        "image": "brain.jpg",
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
        "image": "moogs.jpg",
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
        "image": "dreadbox.jpg",
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
        "image": "wavetable.jpg",
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
        "image": "korg.jpg",
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
        "image": None,
        "images": ["outlaws1.jpg", "outlaws2.jpg"],
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
        "title": "Rodéo — Dark House Rework",
        "original_artist": "Zazie",
        "original_song": "Rodéo",
        "process": (
            "\"C'est la vie, pas le paradis…\"\n\n"
            "Here is my electronic rework of \"Rodéo\" by Zazie — a song I've always loved for "
            "its raw, dark and powerful vision of life: you fall, you get back up, you lose "
            "control… and the ride goes on.\n\n"
            "For this version, I wanted to keep the strength and emotion of the original song "
            "while taking it into TheFAB universe: a groovy 128 BPM ride driven by massive "
            "analog basses from the Moog Subsequent 37 and Moog Matriarch, hypnotic synths "
            "and a powerful electronic beat.\n\n"
            "Dark, melodic, groovy and slightly out of control.\n\n"
            "Welcome to the rodeo."
        ),
        "bpm": 128,
        "youtube_id": "HB4tTHGGmpM",
        "tags": ["dark", "groovy", "moog"],
    },
    {
        "title": "All in You — Melodic Techno Remix",
        "original_artist": "Synapson",
        "original_song": "All in You",
        "process": (
            "Some songs are not just melodies; they are memories.\n\n"
            "A summer afternoon, smiles by the water, friends becoming family, and those "
            "fleeting moments that somehow stay with us forever.\n\n"
            "Through hypnotic synths, deep analog textures and driving melodic rhythms, "
            "TheFAB transforms All In You into a melodic version.\n\n"
            "Because sometimes, the places we seek are already within us. "
            "The light, the memories, the love, the feeling of belonging…\n\n"
            "It's all in you.\n\n"
            "Close your eyes. Follow the melody. Remember the people who made you who you are."
        ),
        "bpm": 130,
        "youtube_id": "D6Ukhn4XAEY",
        "tags": ["melodic", "memories", "summer"],
    },
    {
        "title": "Manitoumani — TheFAB House Rework",
        "original_artist": "M",
        "original_song": "Manitoumani",
        "process": (
            "Under a purple sun, where the sky melts into endless shades of violet, a tribe gathers.\n\n"
            "Barefoot souls, smiling faces, hands reaching for the light. "
            "Ancient rhythms rise from the earth while warm house grooves carry them into the night.\n\n"
            "This rework of Manitoumani is an invitation to let go, to dance without fear, and "
            "to celebrate the simple joy of being together.\n\n"
            "A journey where tribal percussion meets melodic textures, where friendship becomes "
            "rhythm and every heartbeat joins the same pulse.\n\n"
            "For a few precious moments, there are no strangers, no worries, no tomorrow. "
            "Only music. Only movement. Only joy.\n\n"
            "A purple sun above us. Friends around us. And the feeling that the world is exactly "
            "where it should be."
        ),
        "bpm": 128,
        "youtube_id": "jLu5IgDaXno",
        "tags": ["tribal", "house", "melodic"],
    },
    {
        "title": "Cortisone — Melodic Techno Rework",
        "original_artist": "Fauste",
        "original_song": "Cortisone",
        "process": (
            "\"Cortisone\" is my melodic techno reinterpretation of the beautiful song by Fauste, "
            "a talented young Swiss artist.\n\n"
            "With this rework, I wanted to preserve the emotion and vulnerability of the original "
            "lyrics while taking the song into a deep, cinematic electronic universe built around "
            "analog synthesizers, atmospheric textures, powerful basslines and hypnotic grooves.\n\n"
            "This isn't just a remix — it's a complete reinterpretation that transforms an intimate "
            "song into an immersive melodic techno journey.\n\n"
            "If you enjoy artists like Anyma, Tale Of Us, ARTBAT, Ben Böhmer, Massano, "
            "Stephan Bodzin or emotional melodic techno in general, I hope you'll enjoy this version."
        ),
        "bpm": 128,
        "youtube_id": "SRCiZrFoNs8",
        "tags": ["dark", "cinematic", "melodic techno"],
    },
    {
        "title": "Follow Me...",
        "original_artist": "Original composition",
        "original_song": "Follow Me...",
        "process": (
            "Follow Me is built for one purpose: to make the dancefloor move. "
            "Driven by a powerful kick, an acid bassline, and a deep, earth-shaking Moog bass, "
            "the track combines raw club energy with the melodic atmosphere that has become "
            "TheFAB's signature. Hypnotic grooves, evolving textures, and an emotional lead "
            "come together to create a journey that's equally at home in a dark underground "
            "club or on a festival stage. "
            "Turn it up, follow the groove... and let the music take control."
        ),
        "bpm": 130,
        "youtube_id": "3gdVnTj2Nf8",
        "tags": ["acid", "club", "melodic"],
    },
    {
        "title": "Juliette T'es à Poil!!!",
        "original_artist": "Original composition",
        "original_song": "Juliette T'es à Poil!!!",
        "process": (
            "Inspired by the reaction of a friend during a festive New Year's Eve, "
            "Juliette T'es à Poil!!! channels the raw energy of that night into sound. "
            "A bass so deep it shakes the ground and replaces the need for a kick — "
            "this track is a journey into the dark hours of the mind, "
            "hypnotic, heavy, and unapologetically dark."
        ),
        "bpm": 128,
        "youtube_id": "OO0nx94ITSU",
        "tags": ["dark", "hypnotic", "bass"],
    },
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
        "name": "The Best Tiramisu in the World",
        "description": (
            "At least according to my friends. Passed down through an Italian love story "
            "and undefeated through years of friendly cooking competitions, this tiramisu "
            "is rich, light, and dangerously addictive. Try it once — and you may never "
            "look for another recipe again."
        ),
        "key_ingredients": ["Mascarpone", "Savoiardi", "Espresso", "Egg yolks", "Dark rum"],
        "ingredients": [
            "500 g mascarpone, at room temperature",
            "6 egg yolks",
            "120 g caster sugar",
            "300 ml strong espresso, cooled",
            "3 tbsp dark rum (or Marsala)",
            "250 g Savoiardi (ladyfinger biscuits)",
            "Unsweetened cocoa powder, for dusting",
        ],
        "steps": [
            "Whisk egg yolks and sugar together in a large bowl until pale, thick and creamy — about 5 minutes.",
            "Add the mascarpone and fold gently until smooth and fully combined. Do not overwork.",
            "Mix the cooled espresso with the rum in a shallow bowl.",
            "Dip each Savoiardo briefly (1–2 seconds per side) into the espresso. They should be moist but not falling apart.",
            "Lay a layer of dipped biscuits in a deep dish. Cover with half the mascarpone cream.",
            "Add a second layer of dipped biscuits, then the remaining cream.",
            "Smooth the top. Cover and refrigerate for a minimum of 6 hours — overnight is better.",
            "Dust generously with unsweetened cocoa powder just before serving.",
        ],
        "filename": "tiramisu",
        "image": "tiramisu.JPG",
    },
    {
        "name": "TheFAB's Homemade Bolognese",
        "description": (
            "Slow cooking at its finest. Fresh tomatoes, fragrant sage, rich broth and hours "
            "of patience transform simple ingredients into a sauce that tastes like home. "
            "This is the kind of Bolognese that brings everyone back to the table for seconds."
        ),
        "key_ingredients": ["Minced beef", "Fresh tomatoes", "Sage", "Broth", "Red wine"],
        "ingredients": [
            "600 g minced beef (15–20% fat ideal)",
            "800 g ripe fresh tomatoes, roughly chopped (or 2 x 400 g tins)",
            "1 large onion, finely diced",
            "2 carrots, finely diced",
            "2 celery stalks, finely diced",
            "4 cloves garlic, sliced",
            "6 fresh sage leaves",
            "1 small bunch fresh rosemary",
            "150 ml dry red wine",
            "250 ml beef or veal broth",
            "2 tbsp olive oil",
            "Salt and black pepper",
        ],
        "steps": [
            "Heat olive oil in a heavy-based pot over medium-high heat. Add the onion, carrot and celery. Cook gently for 10 minutes until soft.",
            "Add the garlic, sage and rosemary. Cook for 2 more minutes.",
            "Increase heat to high. Add the mince and break it up well. Cook until properly browned — do not rush this step.",
            "Pour in the wine. Let it bubble and reduce completely, about 3 minutes.",
            "Add the tomatoes and broth. Season generously with salt and pepper.",
            "Bring to a boil, then reduce to the lowest simmer possible. Cover partially.",
            "Cook for 2.5 to 3 hours, stirring every 30 minutes. The sauce should be thick, dark and fragrant.",
            "Adjust seasoning before serving. Best with tagliatelle or pappardelle.",
        ],
        "filename": "homemade-bolognese",
        "image": "bolognese.jpg",
    },
    {
        "name": "Beef Wellington",
        "description": (
            "A dish for celebrations and special moments. Tender beef wrapped in golden pastry, "
            "enriched with foie gras, creamy spinach and mushroom duxelles. Elegant enough to "
            "impress your guests, generous enough to satisfy them."
        ),
        "key_ingredients": ["Beef fillet", "Puff pastry", "Foie gras", "Mushroom duxelles", "Creamed spinach"],
        "ingredients": [
            "1 kg beef fillet, centre-cut, well-trimmed",
            "500 g chestnut mushrooms, very finely chopped",
            "200 g baby spinach",
            "150 g foie gras (or smooth duck liver parfait)",
            "2 shallots, finely minced",
            "2 cloves garlic, minced",
            "4 slices Parma ham",
            "500 g all-butter puff pastry",
            "2 egg yolks beaten with 50 ml double cream (egg wash)",
            "1 tbsp Dijon mustard",
            "2 tbsp olive oil",
            "Salt, black pepper, nutmeg",
        ],
        "steps": [
            "Season the beef generously. Sear in very hot oil for 2 minutes per side until deep brown all over. Brush immediately with Dijon mustard. Chill 30 minutes.",
            "Make the duxelles: cook mushrooms, shallot and garlic in butter over medium heat until all moisture has evaporated — about 20 minutes. Season and cool.",
            "Wilt spinach in a pan, squeeze out all water, chop finely, season with salt and nutmeg.",
            "Lay Parma ham on cling film, overlapping. Spread duxelles over it, then the spinach, then dot with foie gras.",
            "Place the chilled beef at one end and roll tightly in the ham layer using the cling film. Twist ends and chill 30 minutes.",
            "Roll out puff pastry. Unwrap the beef roll and place on pastry. Roll to encase completely, sealing edges with egg wash.",
            "Brush all over with egg wash and score lightly. Chill 15 minutes.",
            "Bake at 220°C for 25–30 minutes for medium-rare (internal temp 52°C). Rest 10 minutes before slicing.",
        ],
        "filename": "beef-wellington",
        "image": "beef-wellington.WEBP",
    },
    {
        "name": "Indian Red Bean Pot",
        "description": (
            "A journey through spices and slow cooking. Tender red beans, sweet tomatoes "
            "and layers of mild, spicy and Madras curries create a comforting dish full of "
            "warmth, colour and character. Simple ingredients, extraordinary flavours."
        ),
        "key_ingredients": ["Red kidney beans", "Tomatoes", "Mild curry", "Madras curry", "Spicy curry"],
        "ingredients": [
            "500 g red kidney beans, soaked overnight and rinsed (or 2 x 400 g tins, drained)",
            "400 g tinned chopped tomatoes",
            "2 medium onions, finely chopped",
            "4 cloves garlic, minced",
            "1 tbsp fresh ginger, grated",
            "1 tbsp mild curry powder",
            "1 tsp Madras curry powder",
            "1 tsp hot curry powder",
            "1 tsp ground cumin",
            "1 tsp ground coriander",
            "1/2 tsp turmeric",
            "400 ml coconut milk",
            "2 tbsp vegetable oil",
            "Fresh coriander and basmati rice to serve",
            "Salt and black pepper",
        ],
        "steps": [
            "If using dried beans: boil in unsalted water for 10 minutes, then simmer 45–60 minutes until tender. Drain and set aside.",
            "Heat oil in a large heavy pot. Cook onions over medium heat for 12 minutes until golden.",
            "Add garlic and ginger. Cook 2 minutes.",
            "Add all three curry powders, cumin, coriander and turmeric. Stir constantly for 1 minute to toast the spices.",
            "Add tomatoes. Stir well and cook for 5 minutes until the sauce thickens and the oil separates.",
            "Add the beans and coconut milk. Stir to combine. Season with salt and pepper.",
            "Simmer uncovered on low heat for 25–35 minutes, stirring occasionally, until thick and fragrant.",
            "Adjust seasoning. Serve with basmati rice and fresh coriander.",
        ],
        "filename": "indian-red-bean-pot",
        "image": "indian-red-bean-pot.JPG",
    },
    {
        "name": "Gratin Dauphinois à la Girardet",
        "description": (
            "Proof that true luxury lies in simplicity. Potatoes, cream, garlic and a touch "
            "of nutmeg — nothing more. No cheese, no distractions. Just one of the most "
            "comforting and irresistible dishes ever created."
        ),
        "key_ingredients": ["Waxy potatoes", "Double cream", "Garlic", "Nutmeg", "Butter"],
        "ingredients": [
            "1.2 kg waxy potatoes (Charlotte or Ratte), peeled and very thinly sliced (2 mm)",
            "600 ml double cream",
            "2 cloves garlic, crushed",
            "Freshly grated nutmeg",
            "30 g unsalted butter",
            "Salt and white pepper",
        ],
        "steps": [
            "Preheat oven to 160°C (fan 140°C). Do not wash the sliced potatoes — the starch is essential.",
            "Gently warm the cream with the crushed garlic, a generous grating of nutmeg, salt and white pepper. Do not boil. Remove garlic.",
            "Rub a gratin dish generously with butter. Layer the potatoes evenly, seasoning lightly between each layer.",
            "Pour the warm seasoned cream over the potatoes. It should just reach the top layer.",
            "Dot the surface with the remaining butter.",
            "Bake for 1 hour 30 minutes to 1 hour 45 minutes, until the top is deeply golden and the potatoes are completely tender when pierced.",
            "Rest for 10 minutes before serving. The gratin should hold its shape but be soft and yielding throughout.",
        ],
        "filename": "gratin-dauphinois",
        "image": "gratin-dauphinois.AVIF",
    },
    {
        "name": "Pasta and Sage",
        "description": (
            "Such an easy dish, but full of the love of an Italian family table: good pasta, "
            "butter, garlic, chili, pepper, and a generous handful of sage slowly warmed until "
            "the whole kitchen smells like home."
        ),
        "key_ingredients": ["Pasta", "Butter", "Sage", "Garlic", "Chili"],
        "ingredients": [
            "400 g pasta (tagliatelle or pappardelle)",
            "80 g unsalted butter",
            "3 cloves garlic, sliced",
            "1 small dried chili, crumbled",
            "Large handful of fresh sage leaves",
            "Freshly cracked black pepper",
            "Salt for pasta water",
            "Parmigiano Reggiano to serve",
        ],
        "steps": [
            "Cook pasta in heavily salted boiling water until al dente. Reserve 1 cup of pasta water.",
            "In a wide pan over medium-low heat, melt the butter gently.",
            "Add the garlic and chili. Cook for 2 minutes without colouring.",
            "Add the sage leaves. Let them warm slowly in the butter for 3–4 minutes until fragrant.",
            "Add the drained pasta and toss well, adding a splash of pasta water to loosen.",
            "Season generously with black pepper. Serve immediately with Parmigiano.",
        ],
        "filename": "Pasta_and_Sage",
        "image": "Pasta and Sage.webp",
    },
    {
        "name": "Tarte Fine aux Pommes",
        "description": (
            "A simple, elegant apple tart to finish a meal: thin slices of apple, butter, sugar, "
            "cream, cinnamon and a whisper of nutmeg, baked until the apples are soft and the top "
            "is gently caramelised."
        ),
        "key_ingredients": ["Apples", "Butter", "Sugar", "Cream", "Cinnamon"],
        "ingredients": [
            "1 sheet all-butter puff pastry",
            "3–4 eating apples, peeled, cored and very thinly sliced",
            "40 g unsalted butter, melted",
            "3 tbsp caster sugar",
            "3 tbsp double cream",
            "1 tsp ground cinnamon",
            "A pinch of freshly grated nutmeg",
        ],
        "steps": [
            "Preheat oven to 190°C. Line a baking tray with parchment.",
            "Lay the puff pastry sheet on the tray. Score a 1 cm border around the edge without cutting through.",
            "Brush the centre with half the melted butter.",
            "Arrange apple slices in overlapping rows across the pastry.",
            "Mix the remaining butter, cream, sugar, cinnamon and nutmeg. Spoon evenly over the apples.",
            "Bake for 25–30 minutes until the pastry is golden and the apples are soft and caramelised at the edges.",
            "Rest 5 minutes before slicing. Serve warm, with crème fraîche if you like.",
        ],
        "filename": "Tarte_Fine_aux_Pommes",
        "image": "Tarte Fine aux Pommes.webp",
    },
    {
        "name": "Lemon Ricotta Ravioli",
        "description": (
            "A bright, creamy and very easy pasta dish. Good lemon ricotta ravioli are enough; "
            "all the emotion of the recipe is in the sauce: onions, garlic, butter, fresh lemon, "
            "acidic white wine, cream, chicken broth and a tiny spoon of mild curry."
        ),
        "key_ingredients": ["Ricotta ravioli", "Lemon", "Cream", "White wine", "Mild curry"],
        "ingredients": [
            "500 g fresh ricotta ravioli",
            "1 medium onion, finely diced",
            "2 cloves garlic, minced",
            "40 g unsalted butter",
            "Zest and juice of 1 unwaxed lemon",
            "100 ml dry white wine",
            "150 ml double cream",
            "100 ml chicken broth",
            "1 tsp mild curry powder",
            "Salt and white pepper",
            "Fresh parsley or basil to serve",
        ],
        "steps": [
            "Melt butter in a wide pan over medium heat. Add onion and cook gently for 8 minutes until soft and translucent.",
            "Add garlic and cook for 1 more minute.",
            "Pour in the white wine. Let it bubble and reduce by half, about 2 minutes.",
            "Add the chicken broth, cream, lemon zest, lemon juice and curry powder. Stir well.",
            "Simmer gently for 5 minutes until the sauce thickens slightly. Season with salt and white pepper.",
            "Meanwhile, cook the ravioli in well-salted boiling water according to packet instructions.",
            "Drain and add directly to the sauce. Toss gently to coat.",
            "Serve immediately with fresh herbs and extra lemon zest if desired.",
        ],
        "filename": "Lemon Ricotta Ravioli",
        "image": "ravioli-lemon-cream-sauce.jpg",
    },
]

DOWNLOADS = {
    "High Resolution Songs": [
        {"name": "Jeunesse lève-toi !",  "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/Jeunesse Leve toi.MP3"},
        {"name": "Camarade Président",   "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/Camarade Président.mp3"},
        {"name": "Fin des mondes",       "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/fin des mondes.mp3"},
        {"name": "Give Me Five Jack",    "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/Give me Five Jack.mp3"},
        {"name": "Niagara Champ Brûlé", "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/Niagara champ brule.mp3"},
        {"name": "Rochechouart",         "meta": "MP3 · High quality", "icon": "🎵", "file": "downloads/songs/Rochechouart.mp3"},
    ],
    "Sound Packs": [
        {"name": "Follow Me... — Sound Pack",             "meta": "MP3 · Stems & samples", "icon": "🎛️", "file": "downloads/packs/Sample Pack Follow Me.mp3"},
        {"name": "Matriarche Requiem — Sound Pack",       "meta": "MP3 · Stems & samples", "icon": "🎛️", "file": "downloads/packs/Sound Pack Matriarche requiem.mp3"},
        {"name": "Juliette T'es à Poil!!! — Sound Pack",  "meta": "MP3 · Stems & samples", "icon": "🎛️", "file": "downloads/packs/Sound Pack Juliette.mp3"},
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


# ── Bot-protection helpers ────────────────────────────────────

def _make_form_token():
    """Return a signed timestamp string for the downloads gate form."""
    ts = str(int(time.time()))
    key = app.secret_key.encode() if isinstance(app.secret_key, str) else app.secret_key
    sig = hmac.new(key, ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _verify_form_token(token, min_seconds=3, max_seconds=3600):
    """Return True only if the token is valid and was issued 3 s–1 h ago."""
    try:
        ts_str, sig = token.rsplit(".", 1)
        key = app.secret_key.encode() if isinstance(app.secret_key, str) else app.secret_key
        expected = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        elapsed = time.time() - int(ts_str)
        return min_seconds <= elapsed <= max_seconds
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
def home():
    # Show the first track as the featured track on the home page
    featured = TRACKS[0] if TRACKS else None
    return render_template("home.html", featured=featured, studio=STUDIO_SECTION)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/gear")
def gear():
    return render_template(
        "gear.html",
        gear_categories=GEAR_CATEGORIES,
        studio=STUDIO_SECTION,
        live_set=LIVE_SET_SECTION,
    )


@app.route("/music")
def music():
    return render_template("music.html", tracks=TRACKS)


@app.route("/cooking")
def cooking():
    return render_template("cooking.html", recipes=RECIPES)


@app.route("/downloads", methods=["GET", "POST"])
def downloads():
    if request.method == "POST":
        # Honeypot: bots fill this, humans never see it
        if request.form.get("website", ""):
            return redirect(url_for("downloads"))

        # Timing: reject if form was submitted too fast or token is missing/forged
        if not _verify_form_token(request.form.get("form_token", "")):
            flash("Submission rejected. Please wait a moment and try again.", "error")
            return redirect(url_for("downloads"))

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

    # Soft gate: always show the catalogue. If the visitor has no access,
    # the download buttons are locked and clicking one reveals the email form.
    return render_template(
        "downloads.html",
        downloads=DOWNLOADS,
        has_access=has_download_access(),
        form_token=_make_form_token(),
    )


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
    """Send a newsletter to selected subscribers, or all if none are checked."""
    subject = request.form.get("subject", "").strip()
    body    = request.form.get("body", "").strip()

    if not subject or not body:
        flash("Subject and body are both required.", "error")
        return redirect(url_for("admin_dashboard"))

    selected_ids = [int(i) for i in request.form.getlist("recipient_ids") if i.isdigit()]
    if selected_ids:
        recipients = db.get_subscriber_emails_by_ids(selected_ids)
    else:
        recipients = db.get_subscriber_emails()

    success, message = email_sender.send_newsletter(subject, body, recipients)

    if success:
        db.log_email_send(subject, body, len(recipients))
        flash(f"Email sent. {message}", "success")
    else:
        flash(f"Send failed: {message}", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-subscriber", methods=["POST"])
@admin_required
def admin_delete_subscriber():
    subscriber_id = request.form.get("subscriber_id", type=int)
    if subscriber_id:
        db.delete_subscriber(subscriber_id)
        flash("Subscriber deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/import-subscribers", methods=["POST"])
@admin_required
def admin_import_subscribers():
    import csv
    import io

    file = request.files.get("csv_file")
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    except UnicodeDecodeError:
        flash("Could not read file — please save it as UTF-8 CSV.", "error")
        return redirect(url_for("admin_dashboard"))

    emails = []
    invalid = 0
    for row in csv.reader(stream):
        for cell in row:
            value = cell.strip().lower()
            if not value:
                continue
            if "@" in value and "." in value.split("@")[-1]:
                emails.append(value)
            else:
                invalid += 1

    if not emails:
        flash("No valid email addresses found in the file.", "error")
        return redirect(url_for("admin_dashboard"))

    # Deduplicate within the file itself before hitting the database
    emails = list(dict.fromkeys(emails))

    result = db.bulk_import_subscribers(emails)
    msg = f"Import complete — {result['imported']} added, {result['skipped']} already existed"
    if invalid:
        msg += f", {invalid} invalid lines skipped"
    flash(msg, "success")
    return redirect(url_for("admin_dashboard"))


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # debug=True gives auto-reload during development.
    # Set debug=False (or remove this file's __main__ block) in production.
    app.run(debug=True, port=5000)
