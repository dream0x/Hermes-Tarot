"""Rider–Waite–Smith (RWS) tarot deck data.

Public-domain card meanings + per-card art prompt fragments used by FLUX
to render a visually-coherent custom deck. Keep meanings short — the
oracle voice (Kimi K2.6) does the elaboration.

Run as a module to validate the deck:
    python -m hermes_oracle.tarot.deck --validate
"""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, asdict
from typing import Literal

Arcana = Literal["major", "minor"]
Suit = Literal["wands", "cups", "swords", "pentacles"]


@dataclass(frozen=True)
class Card:
    id: str               # stable slug, e.g. "the-fool", "ace-of-cups"
    name: str             # display name
    arcana: Arcana
    suit: Suit | None
    number: int | None    # 0..21 for Major; 1..14 for Minor (11=Page, 12=Knight, 13=Queen, 14=King)
    keywords: tuple[str, ...]
    upright: str          # one-line core meaning
    reversed: str         # one-line shadow meaning
    art_prompt: str       # FLUX prompt fragment, deck-style is added in render.py


# --- Major Arcana (0–21) ---
MAJOR: list[Card] = [
    Card("the-fool", "The Fool", "major", None, 0,
         ("beginnings", "innocence", "leap"),
         "A fearless leap into the unknown; trust before evidence.",
         "Recklessness, bad timing, refusing to look down.",
         "a young wanderer at a cliff's edge at sunrise, white dog at heel, small bag on a stick"),
    Card("the-magician", "The Magician", "major", None, 1,
         ("manifestation", "skill", "willpower"),
         "Channeling raw will into form; you have what you need.",
         "Manipulation, untapped talent, scattered focus.",
         "a robed figure at an altar with cup, sword, pentacle, and wand, infinity halo above"),
    Card("the-high-priestess", "The High Priestess", "major", None, 2,
         ("intuition", "mystery", "inner voice"),
         "Listen below words; the answer is already in you.",
         "Secrets kept too long, intuition ignored, surface noise.",
         "a veiled priestess between two pillars black and white, crescent moon at her feet, scroll in lap"),
    Card("the-empress", "The Empress", "major", None, 3,
         ("abundance", "nurture", "creation"),
         "Fertile ground; tend what you've planted.",
         "Smothering, stagnation, neglect of the body.",
         "a crowned woman on a cushioned throne in a wheat field, twelve stars above her, river behind"),
    Card("the-emperor", "The Emperor", "major", None, 4,
         ("structure", "authority", "stability"),
         "Build the frame that holds the dream.",
         "Rigidity, control, fragile authority.",
         "a stern bearded king on a stone throne carved with rams, mountains behind, scepter in hand"),
    Card("the-hierophant", "The Hierophant", "major", None, 5,
         ("tradition", "teaching", "belonging"),
         "Wisdom passed down; the lineage you choose.",
         "Dogma, rebellion for its own sake, hollow ritual.",
         "a robed teacher seated between two pillars, two acolytes kneeling, crossed keys at his feet"),
    Card("the-lovers", "The Lovers", "major", None, 6,
         ("union", "choice", "values"),
         "A choice that aligns you with what you love.",
         "Misalignment, avoiding the choice, tempting bargains.",
         "two figures beneath a winged angel and the sun, garden of fruit, mountain rising between them"),
    Card("the-chariot", "The Chariot", "major", None, 7,
         ("willpower", "victory", "drive"),
         "Two opposing forces yoked to your direction.",
         "Aimless motion, burnout, control slipping.",
         "an armored rider on a chariot pulled by black and white sphinxes, starry canopy overhead"),
    Card("strength", "Strength", "major", None, 8,
         ("courage", "compassion", "patience"),
         "Soft hands close the lion's jaws.",
         "Self-doubt, force where tenderness is needed.",
         "a woman in white gently closing a lion's mouth, infinity halo above her, flowers in hair"),
    Card("the-hermit", "The Hermit", "major", None, 9,
         ("solitude", "inner light", "search"),
         "Withdraw to find the lamp; then return.",
         "Isolation that hardens, refusing the path back.",
         "a cloaked figure on a snowy peak holding a lantern with a six-pointed star inside, staff in hand"),
    Card("wheel-of-fortune", "Wheel of Fortune", "major", None, 10,
         ("cycles", "luck", "turning"),
         "What rises will fall and rise again — ride it.",
         "Resisting the turn, blaming the wheel.",
         "a great wheel in cloudy sky inscribed with TARO, sphinx atop, jackal-headed figure descending, snake ascending"),
    Card("justice", "Justice", "major", None, 11,
         ("fairness", "truth", "consequence"),
         "Cause meets effect; the scales settle.",
         "Bias, evasion, debts unpaid.",
         "a crowned figure on a throne holding upright sword and balanced scales, purple drape behind"),
    Card("the-hanged-man", "The Hanged Man", "major", None, 12,
         ("suspension", "perspective", "surrender"),
         "Stop fighting the hold; the view from upside down is the gift.",
         "Stalling, martyrdom, refusing to let go.",
         "a serene figure suspended upside down by one foot from a t-shaped tree, golden halo around his head"),
    Card("death", "Death", "major", None, 13,
         ("ending", "transformation", "release"),
         "What is dying needs to die. New ground beneath.",
         "Clinging to the corpse, fear of change, slow decay.",
         "a skeletal rider on a pale horse carrying a black banner with white rose, sun rising between two towers"),
    Card("temperance", "Temperance", "major", None, 14,
         ("balance", "blending", "patience"),
         "Pour slowly between two cups; alchemy is timing.",
         "Excess, impatience, mixing the wrong elements.",
         "a winged angel pouring water between two golden chalices, one foot on land one on water, irises blooming"),
    Card("the-devil", "The Devil", "major", None, 15,
         ("attachment", "shadow", "indulgence"),
         "Notice the chains are loose. You can step away.",
         "Breaking free, naming the hook, reclaiming power.",
         "a horned figure on a black throne with two chained naked figures below, inverted pentagram above"),
    Card("the-tower", "The Tower", "major", None, 16,
         ("upheaval", "revelation", "collapse"),
         "What was built on lies cannot stand. Let it fall.",
         "Delaying the inevitable, near miss, lessons unlearned.",
         "a tall stone tower struck by lightning, crown blown off, two figures falling against a black sky"),
    Card("the-star", "The Star", "major", None, 17,
         ("hope", "renewal", "guidance"),
         "After the storm, a clear sky and quiet faith.",
         "Despair, disconnection from the source, false hope.",
         "a kneeling nude figure pouring water from two jugs into a pool and onto land, large eight-pointed star above"),
    Card("the-moon", "The Moon", "major", None, 18,
         ("illusion", "dream", "subconscious"),
         "The path is real even when you can't see it whole.",
         "Confusion lifting, deception revealed, fear named.",
         "a yellow moon with a face above a path between two towers, dog and wolf howling, crayfish climbing from water"),
    Card("the-sun", "The Sun", "major", None, 19,
         ("joy", "vitality", "clarity"),
         "Warmth on the face. Things are good.",
         "Hidden gloom, oversharing the light, burning out.",
         "a radiant smiling sun above a child on a white horse holding a red banner, sunflowers behind a wall"),
    Card("judgement", "Judgement", "major", None, 20,
         ("awakening", "calling", "absolution"),
         "A trumpet you can't ignore. Rise to it.",
         "Self-judgment, refusing the call, replaying the past.",
         "an angel blowing a trumpet with a banner, naked figures rising from open coffins below, mountains in distance"),
    Card("the-world", "The World", "major", None, 21,
         ("completion", "wholeness", "integration"),
         "The cycle closes. You are exactly here.",
         "Loose ends, postponed completion, fear of the next cycle.",
         "a dancing figure within a green laurel wreath holding two wands, four creatures in the corners — angel, eagle, lion, bull"),
]

# --- Minor Arcana ---
# Suit themes (for the art prompt): wands=fire/staffs, cups=water/chalices,
# swords=air/blades, pentacles=earth/coins.
SUIT_ELEMENT = {
    "wands": "fire, blooming wooden staff with new leaves",
    "cups": "water, ornate golden chalice",
    "swords": "air, polished steel sword",
    "pentacles": "earth, golden coin engraved with a five-pointed star",
}

# Court ranks: 11=Page, 12=Knight, 13=Queen, 14=King
RANK_NAME = {
    1: "Ace", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
    6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
    11: "Page", 12: "Knight", 13: "Queen", 14: "King",
}

# (suit, rank) -> (keywords, upright, reversed, art_fragment)
# Distilled from RWS. Kept tight on purpose; Kimi expands.
MINOR_DATA: dict[tuple[str, int], tuple[tuple[str, ...], str, str, str]] = {
    # WANDS
    ("wands", 1): (("inspiration", "spark", "potential"),
        "A new fire is lit; act on it before doubt arrives.",
        "Delays, missed timing, an idea that fizzles.",
        "a single flowering staff held in a cloud-borne hand, a castle in the distance"),
    ("wands", 2): (("planning", "vision", "decision"),
        "Standing at the edge of your map; the world is bigger than the deck.",
        "Fear of the bigger world, choosing safety over scope.",
        "a robed figure on a battlement holding a globe, two staffs framing the view"),
    ("wands", 3): (("expansion", "foresight", "ships coming in"),
        "Your earlier work returns. Watch the horizon.",
        "Delays in shipping, plans that don't quite arrive.",
        "a figure on a cliff watching three ships sail in, three staffs around him"),
    ("wands", 4): (("celebration", "home", "milestone"),
        "A threshold crossed; the people you love are here.",
        "Tension at home, celebration that feels hollow.",
        "four staffs forming a flowered arch, two figures dancing beneath, castle behind"),
    ("wands", 5): (("conflict", "competition", "scuffle"),
        "Friction sharpens you; not every fight is an enemy.",
        "Avoiding healthy conflict, internal disarray.",
        "five young men brandishing staffs in mock combat, no winner yet"),
    ("wands", 6): (("victory", "recognition", "return"),
        "Ride in laurelled. Receive what you earned.",
        "Hollow praise, fear of being seen, victory delayed.",
        "a crowned rider on a horse with a laurel-wreathed staff, attendants cheering"),
    ("wands", 7): (("defense", "standing ground", "perseverance"),
        "Hold the high ground; pressure is testimony of your value.",
        "Overwhelmed, retreating from a fight you could win.",
        "a figure on a high rock fending off six staffs from below with one of his own"),
    ("wands", 8): (("speed", "movement", "messages"),
        "Things are moving; ride the current, don't paddle against it.",
        "Stagnation, news that doesn't come, frustration.",
        "eight staffs flying through a clear sky over a green landscape"),
    ("wands", 9): (("resilience", "last stand", "wariness"),
        "Wounded but standing; one more push.",
        "Paranoia, defenses that have outlived their use.",
        "a bandaged figure leaning on a staff, eight more staffs in a row behind him"),
    ("wands", 10): (("burden", "overload", "responsibility"),
        "You are carrying too much. What can you set down?",
        "Releasing the load, delegating, breakdown before breakthrough.",
        "a stooped figure carrying ten heavy staffs toward a distant village"),
    ("wands", 11): (("explorer", "free spirit", "news"),
        "An eager messenger of new fire — listen to the impulse.",
        "Restlessness without follow-through, immature plans.",
        "a youth with feathered hat holding a flowering staff, looking up at it with wonder"),
    ("wands", 12): (("action", "passion", "leaving"),
        "Charge forward; the path is bigger than the village.",
        "Recklessness, leaving without a plan, half-finished journeys.",
        "an armored knight on a rearing horse holding a flowering staff, salamanders on his cloak"),
    ("wands", 13): (("confidence", "warmth", "magnetism"),
        "You are the hearth; people gather to your fire.",
        "Burnout, jealousy, demanding too much of others' light.",
        "a crowned woman on a stone throne holding a sunflower and flowering staff, black cat at her feet"),
    ("wands", 14): (("vision", "leadership", "long view"),
        "Sovereign of your craft; lead by what you make.",
        "Tyranny, impatience, refusing counsel.",
        "a robed king on a throne carved with salamanders holding a flowering staff, lizard at his feet"),

    # CUPS
    ("cups", 1): (("emotion", "new feeling", "love"),
        "A cup overflowing — open to receive.",
        "Numbness, a gift refused, emotion bottled.",
        "a cloud-borne hand offering a chalice with five streams of water and a dove descending"),
    ("cups", 2): (("partnership", "attraction", "mutuality"),
        "Two meet as equals; the third thing is real.",
        "Mismatch, broken trust, withdrawn affection.",
        "two figures exchanging chalices beneath a winged lion's head, garlands above them"),
    ("cups", 3): (("celebration", "friendship", "community"),
        "Lift your cup with the people who saw you.",
        "Gossip, drained social well, exclusion.",
        "three women dancing in a circle raising chalices, fruit at their feet"),
    ("cups", 4): (("apathy", "reflection", "missed offer"),
        "Something is being offered. Are you looking?",
        "Snapping out of the fog, accepting the new.",
        "a youth meditating beneath a tree, three cups before him, a fourth offered by a cloud-hand he ignores"),
    ("cups", 5): (("grief", "loss", "what remains"),
        "Three are spilled. Two still stand. Look behind you.",
        "Acceptance, moving forward, picking up what's left.",
        "a cloaked figure looking down at three spilled cups, two standing cups behind him, river ahead"),
    ("cups", 6): (("nostalgia", "innocence", "kindness"),
        "A childhood gesture, returned with grace.",
        "Stuck in the past, idealizing what wasn't.",
        "a child handing a flowered cup to another in an old courtyard, six cups in total filled with white flowers"),
    ("cups", 7): (("illusion", "options", "fantasy"),
        "Many shining things; few are solid. Choose with eyes open.",
        "Cutting through fantasy, picking one path.",
        "a figure facing seven floating cups in clouds containing different visions: castle, jewels, dragon, wreath"),
    ("cups", 8): (("walking away", "search", "dissatisfaction"),
        "What you have is enough but not yours. Leave well.",
        "Returning to what didn't fit, fear of the unknown.",
        "a cloaked figure walking away from eight stacked cups toward distant mountains under a moon"),
    ("cups", 9): (("contentment", "wish granted", "satisfaction"),
        "A simple, well-fed kind of happy.",
        "Smugness, gluttony, wanting more than you can hold.",
        "a satisfied man seated with arms crossed, nine golden cups arrayed on a curved shelf behind him"),
    ("cups", 10): (("harmony", "family", "fulfillment"),
        "The full rainbow over a real home.",
        "Family rifts, the picture vs. the reality.",
        "a couple watching their two children dance, ten cups arranged in a rainbow above their cottage"),
    ("cups", 11): (("dreaming", "creative spark", "tenderness"),
        "A small messenger from your inner well.",
        "Creative block, oversensitivity, immature feelings.",
        "a youth in blue at the seashore holding a chalice with a fish leaping from it"),
    ("cups", 12): (("romance", "offer", "following the heart"),
        "An invitation arrives on horseback. Open it.",
        "Empty charm, a promise too smooth, false start.",
        "an armored knight riding gently, holding a chalice forward as if offering it to the viewer"),
    ("cups", 13): (("compassion", "intuition", "emotional depth"),
        "She holds the lid open and listens for the answer inside.",
        "Emotional flooding, codependence, drained empath.",
        "a queen on a throne by the sea holding a closed ornate cup like a small chapel, looking down into it"),
    ("cups", 14): (("emotional mastery", "calm in storm", "wise heart"),
        "A still presence amid moving water.",
        "Volatility, suppressed feeling, emotional manipulation.",
        "a king on a stone throne floating on choppy seas, holding a chalice and a lotus scepter"),

    # SWORDS
    ("swords", 1): (("clarity", "breakthrough", "truth"),
        "A clean cut through the fog.",
        "Confusion, words used as weapons, false clarity.",
        "a cloud-borne hand grasping an upright sword piercing a golden crown wreathed in laurel"),
    ("swords", 2): (("stalemate", "denial", "blindfolded choice"),
        "You already know. Lower the blindfold.",
        "Indecision lifting, the truth seen.",
        "a blindfolded woman seated by the sea holding two crossed swords across her chest under a crescent moon"),
    ("swords", 3): (("heartbreak", "grief", "honesty that hurts"),
        "It hurts because it matters. Let it.",
        "Healing, releasing the wound, forgiving slowly.",
        "a red heart pierced by three swords against a stormy gray sky"),
    ("swords", 4): (("rest", "recovery", "stillness"),
        "Lay the sword down. Sleep is strategy.",
        "Restlessness, returning to the fight too early.",
        "a knight effigy lying atop a stone tomb in a chapel, three swords above him on the wall, one beneath"),
    ("swords", 5): (("conflict", "winning ugly", "loss"),
        "You can win and still lose what mattered.",
        "Reconciliation, walking away from a fight you can't win clean.",
        "a smirking figure holding three swords with two more on the ground, dejected figures walking away"),
    ("swords", 6): (("transition", "passage", "leaving behind"),
        "Move to calmer water. Don't look back yet.",
        "Stuck in the crossing, returning to old waters.",
        "a ferryman poling a small boat carrying a cloaked woman and child, six swords standing in the boat"),
    ("swords", 7): (("stealth", "strategy", "deception"),
        "Take what's yours quietly. Or notice what's being taken.",
        "Coming clean, returning what was taken, getting caught.",
        "a figure tiptoeing away from a camp carrying five swords, two left behind"),
    ("swords", 8): (("self-imposed limits", "stuck", "fear"),
        "The blindfold is loose. The swords don't make a wall.",
        "Realizing you can leave, releasing the fear.",
        "a bound and blindfolded figure surrounded by eight upright swords on muddy ground"),
    ("swords", 9): (("anxiety", "nightmare", "rumination"),
        "It is darker in your head than in the room.",
        "Hope returning, naming the worst, sleep again.",
        "a person sitting up in bed with face in hands, nine swords mounted on the wall above"),
    ("swords", 10): (("rock bottom", "ending", "release"),
        "It is over. Tomorrow's sun will still rise.",
        "Slow recovery, refusing to get up, the worst behind you.",
        "a fallen figure face-down by water with ten swords pierced into his back, dawn breaking over distant hills"),
    ("swords", 11): (("curiosity", "sharp questions", "vigilance"),
        "Ask again. The answer is in the pattern.",
        "Gossip, paranoia, words wielded carelessly.",
        "a youth on a windy hilltop holding an upright sword, dark birds flying behind"),
    ("swords", 12): (("charge", "intellect in motion", "haste"),
        "Direct thrust forward. Beware overrunning your reasons.",
        "Aggression, haste, a plan that breaks on contact.",
        "an armored knight charging on a white horse with sword held high, butterflies on his cloak"),
    ("swords", 13): (("clear sight", "honesty", "boundaries"),
        "She does not flatter. She sees you clearly.",
        "Bitterness, harsh words, isolation.",
        "a stern queen on a throne above the clouds holding an upright sword, butterflies and a single cherub"),
    ("swords", 14): (("authority", "judgment", "law"),
        "The verdict is delivered without cruelty.",
        "Tyranny, abuse of authority, cold rationality.",
        "a king on a stone throne holding an upright sword, butterflies behind him, blue robes"),

    # PENTACLES
    ("pentacles", 1): (("opportunity", "seed", "tangible gift"),
        "A real seed in your hand. Plant it.",
        "Lost opportunity, hesitation, scarcity mindset.",
        "a cloud-borne hand offering a single golden pentacle above a lush garden gate"),
    ("pentacles", 2): (("juggling", "balance", "adaptability"),
        "Keep both balls in the air with the same breath.",
        "Overcommitment, dropping a ball, overwhelm.",
        "a juggler dancing while balancing two pentacles in an infinity loop, two ships rising and falling on waves behind him"),
    ("pentacles", 3): (("collaboration", "craft", "build-out"),
        "Three sets of hands, one cathedral.",
        "Friction with collaborators, rework, cutting corners.",
        "a stonemason working in a cathedral arch with two figures consulting blueprints, three pentacles set into the arch"),
    ("pentacles", 4): (("holding tight", "security", "control"),
        "Notice your grip. What is it costing you?",
        "Loosening the grip, generosity returning.",
        "a crowned figure clutching one pentacle to his chest, one balanced on his head, two beneath his feet"),
    ("pentacles", 5): (("hardship", "lack", "feeling outside"),
        "The light is on inside the church. Knock.",
        "Recovery, asking for help, finding shelter.",
        "two ragged figures struggling through snow past a stained-glass window, five pentacles forming a tree pattern in the glass"),
    ("pentacles", 6): (("generosity", "give and take", "balance of resources"),
        "Notice who is holding the scales.",
        "Strings attached, debt, uneven generosity.",
        "a wealthy merchant weighing coins on a scale and dropping them into the hands of two kneeling figures"),
    ("pentacles", 7): (("patience", "assessment", "harvest pause"),
        "It's growing. Don't dig it up to check.",
        "Impatience, abandoning the work too early.",
        "a farmer leaning on his hoe, surveying a vine bearing seven pentacles"),
    ("pentacles", 8): (("craft", "diligence", "mastery in motion"),
        "Heads down. The hours add up.",
        "Burnout from repetition, uninspired work, perfectionism.",
        "an artisan at a workbench hammering pentacles, six finished above him on display, one in progress"),
    ("pentacles", 9): (("self-sufficiency", "earned ease", "elegance"),
        "The garden is yours. Walk in it slowly.",
        "Loneliness in success, performance of luxury.",
        "an elegantly dressed woman in a vineyard with a hooded falcon on her glove, nine pentacles among the leaves"),
    ("pentacles", 10): (("legacy", "wealth across generations", "rooted family"),
        "What you build outlasts you.",
        "Family wealth tensions, golden cage, rootlessness.",
        "an old patriarch with two dogs, a younger couple and a child in a courtyard arch, ten pentacles arranged as the Tree of Life"),
    ("pentacles", 11): (("study", "new venture", "tangible message"),
        "A small fact arrives that changes a plan.",
        "Procrastination, studying instead of starting.",
        "a youth in a green field examining a single pentacle held above his head"),
    ("pentacles", 12): (("steady progress", "reliability", "patience"),
        "Slow horse, finished journey.",
        "Stalled, stubbornness, going through the motions.",
        "an armored knight on a stationary draft horse holding a single pentacle, plowed fields behind"),
    ("pentacles", 13): (("nurture of resources", "groundedness", "abundance"),
        "She tends the soil and the soul together.",
        "Self-neglect, financial worry, smothering.",
        "a queen on a throne in a flowering garden cradling a large pentacle, rabbits and roses around her"),
    ("pentacles", 14): (("provider", "stable wealth", "material mastery"),
        "Solid ground; share the harvest.",
        "Greed, status anxiety, miserliness.",
        "a robed king on a stone throne carved with bulls, a pentacle on his lap, lush vines climbing"),
}


def _build_minor() -> list[Card]:
    out: list[Card] = []
    for (suit, rank), (kw, up, rev, art) in MINOR_DATA.items():
        rank_name = RANK_NAME[rank]
        name = f"{rank_name} of {suit.capitalize()}"
        slug = f"{rank_name.lower()}-of-{suit}"
        # Compose final art prompt with suit element
        art_full = f"{art}, {SUIT_ELEMENT[suit]}"
        out.append(Card(slug, name, "minor", suit, rank, kw, up, rev, art_full))
    return out


MINOR: list[Card] = _build_minor()
DECK: list[Card] = MAJOR + MINOR
DECK_BY_ID: dict[str, Card] = {c.id: c for c in DECK}


def draw(n: int = 1, *, allow_reversed: bool = True, rng: random.Random | None = None) -> list[tuple[Card, bool]]:
    """Draw `n` cards without replacement. Each is (card, is_reversed)."""
    rng = rng or random.SystemRandom()
    chosen = rng.sample(DECK, n)
    return [(c, rng.random() < 0.5 if allow_reversed else False) for c in chosen]


def by_id(card_id: str) -> Card:
    return DECK_BY_ID[card_id]


def validate() -> None:
    assert len(MAJOR) == 22, f"expected 22 Major Arcana, got {len(MAJOR)}"
    assert len(MINOR) == 56, f"expected 56 Minor Arcana, got {len(MINOR)}"
    assert len(DECK) == 78, f"expected 78 cards total, got {len(DECK)}"
    ids = [c.id for c in DECK]
    assert len(ids) == len(set(ids)), "duplicate card ids detected"
    for c in DECK:
        assert c.upright and c.reversed and c.art_prompt, f"missing field on {c.id}"
        if c.arcana == "minor":
            assert c.suit in SUIT_ELEMENT, f"bad suit on {c.id}"
            assert c.number in RANK_NAME, f"bad rank on {c.id}"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--validate", action="store_true")
    p.add_argument("--draw", type=int, default=0)
    p.add_argument("--show", type=str, help="card id to show")
    args = p.parse_args()

    if args.validate:
        validate()
        print(f"OK: {len(DECK)} cards, {len(MAJOR)} Major + {len(MINOR)} Minor")
    if args.draw:
        for card, rev in draw(args.draw):
            tag = "(reversed)" if rev else ""
            print(f"  {card.name} {tag}")
            print(f"    -> {card.reversed if rev else card.upright}")
    if args.show:
        c = by_id(args.show)
        import json as _json
        print(_json.dumps(asdict(c), indent=2))
    if not (args.validate or args.draw or args.show):
        p.print_help()
        sys.exit(0)
