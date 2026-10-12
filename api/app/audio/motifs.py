"""From 521 AudioSet classes to the handful of things a postcard can show.

YAMNet's own labels are stored untouched. This module groups them into
motifs, which do two jobs: they are the short tags people see ("Rain",
"Birdsong") and they tell the postcard painter what to draw.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.audio.tagger import Label


@dataclass(frozen=True)
class Motif:
    slug: str
    name: str  # shown in the UI
    phrase: str  # used in the image prompt: "the sound of {phrase}"
    classes: tuple[str, ...]
    weight: float = 1.0


_MUSIC_GENRES = (
    "Pop music", "Hip hop music", "Beatboxing", "Rock music", "Heavy metal", "Punk rock", "Grunge",
    "Progressive rock", "Rock and roll", "Psychedelic rock", "Rhythm and blues", "Soul music", "Reggae",
    "Country", "Swing music", "Bluegrass", "Funk", "Folk music", "Middle Eastern music", "Jazz", "Disco",
    "Classical music", "Opera", "Electronic music", "House music", "Techno", "Dubstep", "Drum and bass",
    "Electronica", "Electronic dance music", "Ambient music", "Trance music", "Music of Latin America",
    "Salsa music", "Flamenco", "Blues", "Music for children", "New-age music", "Vocal music", "A capella",
    "Music of Africa", "Afrobeat", "Christian music", "Gospel music", "Music of Asia", "Carnatic music",
    "Music of Bollywood", "Ska", "Traditional music", "Independent music", "Song", "Background music",
    "Theme music", "Jingle (music)", "Soundtrack music", "Lullaby", "Video game music", "Christmas music",
    "Dance music", "Wedding music", "Happy music", "Sad music", "Tender music", "Exciting music",
    "Angry music", "Scary music",
)
_INSTRUMENTS = (
    "Music", "Musical instrument", "Plucked string instrument", "Guitar", "Electric guitar", "Bass guitar",
    "Acoustic guitar", "Steel guitar, slide guitar", "Tapping (guitar technique)", "Strum", "Banjo", "Sitar",
    "Mandolin", "Zither", "Ukulele", "Keyboard (musical)", "Piano", "Electric piano", "Organ",
    "Electronic organ", "Hammond organ", "Synthesizer", "Sampler", "Harpsichord", "Percussion", "Drum kit",
    "Drum machine", "Drum", "Snare drum", "Rimshot", "Drum roll", "Bass drum", "Timpani", "Tabla", "Cymbal",
    "Hi-hat", "Wood block", "Tambourine", "Rattle (instrument)", "Maraca", "Mallet percussion",
    "Marimba, xylophone", "Glockenspiel", "Vibraphone", "Steelpan", "Orchestra", "Brass instrument",
    "French horn", "Trumpet", "Trombone", "Bowed string instrument", "String section", "Violin, fiddle",
    "Pizzicato", "Cello", "Double bass", "Wind instrument, woodwind instrument", "Flute", "Saxophone",
    "Clarinet", "Harp", "Harmonica", "Accordion", "Bagpipes", "Didgeridoo", "Shofar", "Theremin",
    "Scratching (performance technique)", "Singing", "Choir", "Yodeling", "Chant", "Mantra", "Child singing",
    "Synthetic singing", "Rapping", "Humming", "Whistling",
)

MOTIFS: tuple[Motif, ...] = (
    Motif("rain", "Rain", "rain falling", ("Rain", "Raindrop", "Rain on surface")),
    Motif("storm", "Thunder", "a thunderstorm", ("Thunderstorm", "Thunder")),
    Motif("water", "Running water", "running water",
          ("Stream", "Waterfall", "Gurgling", "Trickle, dribble", "Pour", "Liquid", "Splash, splatter", "Gush",
           "Fill (with liquid)", "Slosh", "Drip")),
    Motif("waves", "Waves", "waves on the shore",
          ("Ocean", "Waves, surf", "Boat, Water vehicle", "Sailboat, sailing ship", "Rowboat, canoe, kayak",
           "Motorboat, speedboat", "Ship", "Foghorn")),
    Motif("wind", "Wind", "wind in the trees", ("Wind", "Rustling leaves", "Wind noise (microphone)", "Rustle")),
    Motif("birds", "Birdsong", "birdsong",
          ("Bird", "Bird vocalization, bird call, bird song", "Chirp, tweet", "Squawk", "Pigeon, dove", "Coo",
           "Crow", "Caw", "Owl", "Hoot", "Bird flight, flapping wings", "Fowl", "Chicken, rooster", "Cluck",
           "Crowing, cock-a-doodle-doo", "Turkey", "Gobble", "Duck", "Quack", "Goose", "Honk")),
    Motif("insects", "Insects", "crickets and insects",
          ("Insect", "Cricket", "Mosquito", "Fly, housefly", "Buzz", "Bee, wasp, etc.")),
    Motif("animals", "Animals", "animals calling",
          ("Domestic animals, pets", "Dog", "Bark", "Yip", "Howl", "Bow-wow", "Growling", "Whimper (dog)", "Cat",
           "Purr", "Meow", "Caterwaul", "Livestock, farm animals, working animals", "Horse", "Clip-clop",
           "Neigh, whinny", "Cattle, bovinae", "Moo", "Cowbell", "Pig", "Oink", "Goat", "Bleat", "Sheep", "Frog",
           "Croak", "Canidae, dogs, wolves", "Roar", "Roaring cats (lions, tigers)")),
    Motif("traffic", "Traffic", "passing traffic",
          ("Vehicle", "Motor vehicle (road)", "Car", "Vehicle horn, car horn, honking", "Toot", "Car alarm",
           "Skidding", "Tire squeal", "Car passing by", "Race car, auto racing", "Truck", "Air brake",
           "Air horn, truck horn", "Reversing beeps", "Bus", "Motorcycle", "Traffic noise, roadway noise", "Engine",
           "Light engine (high frequency)", "Medium engine (mid frequency)", "Heavy engine (low frequency)",
           "Engine knocking", "Engine starting", "Idling", "Accelerating, revving, vroom", "Emergency vehicle",
           "Police car (siren)", "Ambulance (siren)", "Fire engine, fire truck (siren)", "Siren",
           "Ice cream truck, ice cream van")),
    Motif("train", "Trains", "a train going by",
          ("Rail transport", "Train", "Train whistle", "Train horn", "Railroad car, train wagon",
           "Train wheels squealing", "Subway, metro, underground", "Clickety-clack", "Steam whistle")),
    Motif("aircraft", "Aircraft", "an aircraft overhead",
          ("Aircraft", "Aircraft engine", "Jet engine", "Propeller, airscrew", "Helicopter",
           "Fixed-wing aircraft, airplane")),
    Motif("bells", "Bells", "bells ringing",
          ("Bell", "Church bell", "Jingle bell", "Bicycle bell", "Chime", "Wind chime",
           "Change ringing (campanology)", "Tubular bells", "Singing bowl", "Gong", "Ding-dong", "Jingle, tinkle",
           "Ding")),
    Motif("music", "Music", "music drifting past", _INSTRUMENTS + _MUSIC_GENRES),
    Motif("market", "Bustle", "a busy crowd",
          ("Chatter", "Crowd", "Hubbub, speech noise, speech babble", "Cheering", "Applause", "Clapping",
           "Children playing", "Children shouting", "Laughter", "Cash register", "Coin (dropping)",
           "Inside, public space")),
    Motif("cafe", "Cafe clatter", "cups and plates",
          ("Dishes, pots, and pans", "Cutlery, silverware", "Chink, clink", "Glass", "Chopping (food)",
           "Frying (food)", "Sizzle", "Boiling", "Stir", "Microwave oven", "Blender", "Water tap, faucet",
           "Sink (filling or washing)")),
    Motif("footsteps", "Footsteps", "footsteps", ("Walk, footsteps", "Run", "Shuffle", "Bicycle", "Skateboard")),
    Motif("fire", "Fire", "a crackling fire", ("Fire", "Crackle")),
    Motif("fireworks", "Fireworks", "fireworks",
          ("Fireworks", "Firecracker", "Burst, pop", "Explosion", "Boom", "Bang", "Eruption")),
    Motif("works", "Works", "tools at work",
          ("Tools", "Hammer", "Jackhammer", "Sawing", "Filing (rasp)", "Sanding", "Power tool", "Drill", "Chainsaw",
           "Lawn mower", "Sewing machine", "Wood", "Chop")),
    # Broadband noise says little about a place, so it only wins when nothing else is there.
    Motif("hum", "Hum", "a low steady hum",
          ("White noise", "Pink noise", "Static", "Noise", "Environmental noise", "Hum", "Mains hum",
           "Mechanical fan", "Air conditioning", "Silence", "Vibration", "Throbbing", "Whir", "Rumble"),
          weight=0.35),
)

MOTIF_BY_SLUG: dict[str, Motif] = {m.slug: m for m in MOTIFS}
_CLASS_TO_MOTIF: dict[str, Motif] = {name: motif for motif in MOTIFS for name in motif.classes}
MOTIF_FLOOR = 0.08
FALLBACK = "hum"


@dataclass(frozen=True)
class Tag:
    slug: str
    name: str
    score: float


def pick_motifs(labels: list[Label], limit: int = 3) -> list[Tag]:
    """The strongest motifs in a clip, best first. Always returns at least one."""
    best: dict[str, float] = {}
    for label in labels:
        motif = _CLASS_TO_MOTIF.get(label.name)
        if motif is None:
            continue
        score = label.score * motif.weight
        if score > best.get(motif.slug, 0.0):
            best[motif.slug] = score
    ranked = sorted(best.items(), key=lambda item: (-item[1], item[0]))
    tags = [
        Tag(slug=slug, name=MOTIF_BY_SLUG[slug].name, score=round(score, 4))
        for slug, score in ranked
        if score >= MOTIF_FLOOR
    ][:limit]
    if not tags:
        tags = [Tag(slug=FALLBACK, name=MOTIF_BY_SLUG[FALLBACK].name, score=0.0)]
    return tags


def unknown_classes(class_names: list[str]) -> list[str]:
    """Motif class names that the tagger does not know. Used by a test to catch typos."""
    known = set(class_names)
    return [name for name in _CLASS_TO_MOTIF if name not in known]
