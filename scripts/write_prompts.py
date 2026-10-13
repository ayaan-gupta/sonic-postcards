"""Writes assets/prompts.md, the image request log, from the table below and what is on disk.

    api/.venv/bin/python scripts/write_prompts.py      (or: make interim)

A request is "delivered" once its file exists in assets/generated; until then
the code-drawn file at the same path in assets/interim is used.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.audio.motifs import MOTIFS  # noqa: E402

STYLE = (
    "Vintage travel postcard illustration painted in gouache: flat opaque colour, visible dry-brush texture, soft "
    "uneven edges, matte finish, simple bold shapes, mid-century travel poster composition. Limited palette: "
    "vermilion #e2583a, ink navy #1d2440, cream #f6f0e1, sky blue #73b6cf, teal #2f86a8, sage #559b82, ochre #e6c684, "
    "warm yellow #f8d368. No text, no lettering, no numbers, no watermark."
)

STAMP_SUBJECT = {
    "rain": "a small figure in a dark coat under a red umbrella, light rain streaks, one flat grey cloud",
    "storm": "a dark flat-bottomed cloud with one yellow lightning bolt over a low horizon",
    "water": "a stone fountain with two arcs of water falling into a round basin",
    "waves": "a small sailboat with one red and one white sail on a blue sea with white wave strokes",
    "wind": "a red and yellow diamond kite with a ribbon tail, one white swirl of wind",
    "birds": "a plump dark bird with a red beak perched on a wire, two small birds flying far off",
    "insects": "tall dark grass at night with five glowing fireflies, deep navy sky",
    "animals": "one white woolly sheep with a dark face standing on a field",
    "traffic": "a small rounded red car seen from the side on a dark road",
    "train": "a small steam locomotive pulling red carriages, puffs of white smoke",
    "aircraft": "a white airliner with a red tail climbing to the right, two thin contrails",
    "bells": "a single large golden bell with a clapper, curved lines of sound either side, dusk sky",
    "music": "two joined musical quavers in cream on a dusk sky of purple and orange bands",
    "market": "a market stall with a red and cream striped awning and a counter heaped with fruit",
    "cafe": "a white coffee cup on a red saucer with two curls of steam",
    "footsteps": "a small figure in a red coat walking, seen from behind, on a pale path",
    "fire": "a campfire of crossed logs with red, yellow and cream flames and sparks at night",
    "fireworks": "one large firework burst of gold and red rays in a navy night sky",
    "works": "a red tower crane with a hook and a hanging load against a blue sky",
    "hum": "a pale yellow sun over two calm rolling hills, nothing else",
}


def requests() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for motif in MOTIFS:
        items.append({
            "name": f"{motif.name.lower()} stamp",
            "prompt": f"{STYLE} A postage stamp with a perforated edge and a cream paper margin, seen flat from the front. Inside its thin "
                      f"navy frame: {STAMP_SUBJECT[motif.slug]}. Leave a blank cream band along the bottom tenth of the stamp, inside the "
                      "perforations: the app prints the stamp's value there.",
            "spec": "300x372 px, about 4:5, transparent outside the perforated edge, PNG.",
            "path": f"stamps/{motif.slug}.png",
            "use": f"The stamp on every postcard whose strongest sound is \"{motif.name}\". Without it the code-drawn stamp is used.",
        })
    items.append({
        "name": "blank postmark",
        "prompt": "A blank rubber-stamp postmark in black ink on a transparent background, seen flat. On the left, two concentric circles: "
                  "a heavy outer ring and a thinner inner ring with a clear gap between them. On the right, six parallel wavy cancellation "
                  "lines running away from the circles. The ink is uneven and slightly worn, as a real hand stamp prints. Nothing inside "
                  "the rings and no lettering anywhere: the app sets the city and date itself.",
        "spec": "760x400 px, 19:10, transparent background, single colour (black or #1d2440), PNG. Outer ring about 368 px across, centred 200 px from the left edge.",
        "path": "postmark/ring.png",
        "use": "Printed over the top right of every postcard, under the city, date and time of day that the template adds.",
    })
    items.append({
        "name": "logo",
        "prompt": "App mark, flat vector look with a faint gouache grain: a vermilion #e2583a postage stamp with a perforated edge. Inside a thin "
                  "cream #f6f0e1 rounded frame, seven vertical cream bars of different heights form a sound waveform, tallest in the middle. "
                  "No text.",
        "spec": "512x512 px, 1:1, transparent background, PNG.",
        "path": "brand/logo.png",
        "use": "The mark next to the name in the header of every page.",
    })
    for size in (192, 512):
        items.append({
            "name": f"app icon {size}",
            "prompt": "The same mark as SP-022 (vermilion perforated stamp, cream frame, seven-bar waveform), centred, no text.",
            "spec": f"{size}x{size} px, 1:1, transparent background, PNG.",
            "path": f"brand/icon-{size}.png",
            "use": "Favicon, Apple touch icon and installed app icon.",
        })
    items.append({
        "name": "maskable app icon",
        "prompt": "The waveform and cream frame of SP-022 on a full-bleed vermilion #e2583a square with no perforations, the frame kept inside "
                  "the middle 60% so that a circular mask does not cut it. No text.",
        "spec": "512x512 px, 1:1, opaque, PNG.",
        "path": "brand/icon-maskable-512.png",
        "use": "Android adaptive icon.",
    })
    scenes = (
        ("listen", "onboarding: listen", "A sunny meadow path with a cafe table under a striped red and cream parasol, a few small birds on a fence "
         "and a flock in a bright blue sky. Calm, inviting, daytime.", "720x540 px, 4:3, arched top (a rounded arch window shape) on a transparent background, PNG.",
         "First step of the welcome sheet and the About page: listen for ten seconds."),
        ("place", "onboarding: place", "A calm bay at dawn with a rising sun, two small sailboats, a striped lighthouse on a headland and a sandy beach. "
         "A large vermilion map pin with a cream dot stands in the middle of the water.", "720x540 px, 4:3, arched top on a transparent background, PNG.",
         "Second step: pin it, roughly. Also the empty state of the Nearby tab before a location is shared."),
        ("send", "onboarding: send", "A steam train crossing a stone viaduct at dusk, orange and purple sky, a low sun, white swirls of wind and a few "
         "falling leaves.", "720x540 px, 4:3, arched top on a transparent background, PNG.", "Third step: get a postcard back."),
    )
    for slug, name, subject, spec, use in scenes:
        items.append({"name": name, "prompt": f"{STYLE} {subject}", "spec": spec, "path": f"onboarding/{slug}.png", "use": use})
    items.append({
        "name": "empty state: quiet",
        "prompt": f"{STYLE} A still night landscape of dark blue rolling hills, a crescent moon, one flat cloud, a few stars, a fence and a winding path. Nobody about.",
        "spec": "560x360 px, 14:9, rounded corners (36 px) on a transparent background, PNG.",
        "path": "empty/quiet.png",
        "use": "Shown when there are no postcards nearby, when a postcard link is dead, and on the offline page.",
    })
    items.append({
        "name": "empty state: hush",
        "prompt": f"{STYLE} A town square at dusk with lit windows, striped awnings, a cafe table under a parasol and a market stall. Two tiny distant figures, no faces.",
        "spec": "560x360 px, 14:9, rounded corners (36 px) on a transparent background, PNG.",
        "path": "empty/hush.png",
        "use": "Shown next to the message when a clip is refused for being mostly speech.",
    })
    return items


def main() -> None:
    items = requests()
    generated = ROOT / "assets" / "generated"
    delivered = sum(1 for item in items if (generated / item["path"]).is_file())
    lines = [
        "# Image requests",
        "",
        f"{len(items)} images requested, {delivered} delivered. Regenerate this file with `make interim` after adding files.",
        "",
        "These are design-time assets. Save each file at the path given and it is picked up on the next request: anything in "
        "`assets/generated` wins over the code-drawn file of the same name in `assets/interim`, one file at a time. Both the API "
        "(stamps and postmark, composited into postcards) and the web app (`/art/...`) follow that rule.",
        "",
        "The postcard pictures themselves are not in this list. They are made at runtime, once per postcard, by the image provider "
        "(the built-in painter unless `IMAGE_PROVIDER` says otherwise). All lettering on a postcard is set by the template in code.",
        "",
        "**Style bible:** vintage travel postcard, gouache look, a stamp in the corner and a postmark with the date and city name.",
        "",
        "**Palette:** `#e2583a` `#1d2440` `#f6f0e1` `#73b6cf` `#2f86a8` `#559b82` `#e6c684` `#f8d368`",
        "",
    ]
    for number, item in enumerate(items, 1):
        done = (generated / item["path"]).is_file()
        lines += [
            f"## SP-{number:03d} {item['name']}",
            "",
            f"- **Status:** {'delivered (in use)' if done else 'requested (code-drawn interim file in use)'}",
            f"- **Prompt:** {item['prompt']}",
            f"- **Spec:** {item['spec']}",
            f"- **Save to:** `assets/generated/{item['path']}`",
            f"- **Used for:** {item['use']}",
            "",
        ]
    (ROOT / "assets" / "prompts.md").write_text("\n".join(lines), encoding="utf-8")
    missing = [item["path"] for item in items if not (ROOT / "assets" / "interim" / item["path"]).is_file()]
    print(f"{len(items)} requests written, {delivered} delivered" + (f", MISSING interim files: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
