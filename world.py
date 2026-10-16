"""
Wayfar 1444 Planetary and On-Demand Spawn ($ods) Engine.
Renders the side-by-side ANSI tactical terrain map and procedural room descriptions.
"""

import time
import re
from typing import Dict, List, Tuple, Any
from perlin import fbm2d, raw_noise2d

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"

BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"
BG_DARKGREY = "\033[100m"

# Biome definitions with background ANSI styling
BIOMES = {
    "water": {
        "name": "water",
        "bg": BG_BLUE,
        "fg": FG_WHITE,
        "char_options": ["..", "00", "  ", "~~"]
    },
    "marsh": {
        "name": "marsh",
        "bg": BG_CYAN,
        "fg": FG_BLACK,
        "char_options": ["..", "::", "00", "  "]
    },
    "forest": {
        "name": "forest",
        "bg": BG_GREEN,
        "fg": FG_WHITE,
        "char_options": ["00", "..", "  ", "--"]
    },
    "grassland": {
        "name": "grassland",
        "bg": BG_YELLOW,
        "fg": FG_BLACK,
        "char_options": ["..", "  ", "00", "--"]
    },
    "desert": {
        "name": "desert",
        "bg": BG_RED,
        "fg": FG_YELLOW,
        "char_options": ["..", "00", "  ", "--"]
    },
    "canyon": {
        "name": "canyon",
        "bg": BG_RED,
        "fg": FG_WHITE,
        "char_options": ["..", "00", "--", "  "]
    },
    "rocky": {
        "name": "rocky",
        "bg": BG_WHITE,
        "fg": FG_BLACK,
        "char_options": ["00", "..", "##", "  "]
    },
    "metallic_wasteland": {
        "name": "metallic wasteland",
        "bg": BG_DARKGREY,
        "fg": FG_CYAN,
        "char_options": ["--", "00", "..", "  "]
    },
    "crystalline": {
        "name": "crystalline",
        "bg": BG_MAGENTA,
        "fg": FG_WHITE,
        "char_options": ["::", "00", "..", "  "]
    }
}

# Planet Definitions (100x100 grid per Wayfar specifications)
PLANETS = {
    "WY-1444": {
        "name": "WY-1444",
        "theme": "The rugged homeworld. Teeming with mutated ecology, ancient debris, and diverse climates.",
        "start_pos": (24, 21),
        "scale_x": 7.5,
        "scale_y": 7.5,
        "biomes": ["water", "forest", "grassland", "rocky", "metallic_wasteland"],
        "creatures": ["muta-chicken", "wire asp", "feral drone", "rust hound", "spore crab"],
        "items": ["inert metal fragment", "copper wire strand", "broken sensor"]
    },
    "MO-52": {
        "name": "MO-52",
        "theme": "A searing desert world of deep canyons, exposed needle spires, and shifting dunes.",
        "start_pos": (30, 62),
        "scale_x": 5.0,
        "scale_y": 5.0,
        "biomes": ["canyon", "desert", "metallic_wasteland", "rocky"],
        "creatures": ["silica scorpion", "dune stalker", "sun beetle", "wire asp"],
        "items": ["metallic needle shard", "fused silicate", "solar collector fragment"]
    },
    "AE-1655": {
        "name": "AE-1655",
        "theme": "A primeval wetland anomaly planet dotted with murky pools and shimmering crystalline circles.",
        "start_pos": (50, 50),
        "scale_x": 6.0,
        "scale_y": 6.0,
        "biomes": ["water", "marsh", "crystalline", "rocky"],
        "creatures": ["marsh leech", "crystalline crawler", "plasma tick", "muta-chicken"],
        "items": ["bioluminescent spore", "crystalline shard", "alkali crust"]
    }
}

# Procedural Descriptors matching Wayfar 1444 text templates
DESCRIPTIONS_FLORA = [
    "A modest patch of native flora is growing here.",
    "A thicket of native trees is growing here.",
    "A few plants grow here.",
    "A lone tree is standing here.",
    "Several exotic plants are growing in a patch here.",
    "Clumps of dry, fibrous shrubbery struggle against the elements.",
    "Clusters of pale lichen cling stubbornly to the surface.",
    "A tangled mass of thorned creepers spreads across the terrain."
]

DESCRIPTIONS_GEOLOGY = [
    "Where the ground has eroded, inert metal is exposed.",
    "Where the ground has eroded metallic needle structures are exposed.",
    "A range of sand dunes has accumulated here.",
    "Delicate net-like structures are amongst the earth.",
    "A few deposits of soil litter the area.",
    "Vast sheets of oxidized composite plating jut out from the silt.",
    "Cracked bedrock and fractured basalt make footing treacherous.",
    "Finely powdered silicate covers the ground like grey ash."
]

DESCRIPTIONS_THERMAL = [
    "There are a couple of warm spots in the area, caused by thermal energy welling up from the planet's core.",
    "Thermal vapors vent lazily from thin cracks in the crust.",
    "A faint tectonic vibration hums continuously through your feet.",
    "The air is cool, carrying the sharp scent of ozone and mineral salts.",
    "A dry, persistent wind sweeps across the open expanse."
]

DESCRIPTIONS_WATER = [
    "A small pool of water has collected here.",
    "There is a puddle of water here.",
    "A slick sheen of condensation covers the lower stones.",
    "A sluggish trickle of dark brine seeps along an incline.",
    "The ground here is baked bone dry, devoid of all moisture."
]

ROOM_NAMES_BY_BIOME = {
    "desert": ["choking canyon", "blistered rise", "dune terrace", "scour basin", "sun-baked shelf"],
    "canyon": ["choking canyon", "narrow gulch", "crimson rift", "echoing fissure", "steep gorge"],
    "forest": ["hidden stand", "verdant grove", "thick copse", "shadowed bower", "pine hollow"],
    "water": ["liquid water", "murky pool", "dark shallows", "deep channel", "stagnant basin"],
    "marsh": ["murky pool", "spore fen", "quaking mire", "reed marsh", "silt sink"],
    "grassland": ["open prairie", "rolling savanna", "windy steppe", "tallgrass shelf", "whispering expanse"],
    "rocky": ["towering hill", "elevated range", "craggy bluff", "jagged summit", "scree field"],
    "metallic_wasteland": ["ruined concourse", "needle waste", "slag terrace", "shattered foundry", "reactor verge"],
    "crystalline": ["crystalline circle", "shimmering terrace", "prism hollow", "vitrified crest", "resonance pit"]
}

CARDINAL_DIRECTIONS = {
    "north": (0, -1),
    "northeast": (1, -1),
    "east": (1, 0),
    "southeast": (1, 1),
    "south": (0, 1),
    "southwest": (-1, 1),
    "west": (-1, 0),
    "northwest": (-1, -1)
}


def pseudo_hash(planet_id: str, x: int, y: int, seed: int = 42) -> int:
    """Deterministic integer hash for world coordinates."""
    key = f"{planet_id}:{x}:{y}:{seed}"
    val = 0
    for char in key:
        val = (val * 31 + ord(char)) & 0xFFFFFFFF
    return val


def strip_ansi(text: str) -> str:
    """Removes ANSI escape codes to compute visible character length."""
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_regex.sub("", text)


def biome_at(planet_id: str, x: int, y: int) -> str:
    """Return the stable biome assigned to a planetary coordinate.

    The Hellcore notes use one octave when indexing a finite biome list.  The
    extension can still return the list length at the upper edge, so clamp that
    edge instead of wrapping it back to biome zero (which creates false seams).
    Both room generation and the tactical map use this function.
    """
    planet = PLANETS[planet_id]
    biomes = planet["biomes"]
    index = fbm2d(x % 100, y % 100, planet["scale_x"], planet["scale_y"], len(biomes), octaves=1)
    return biomes[max(0, min(index, len(biomes) - 1))]


class Room:
    """Represents a procedurally spawned room in the On Demand Spawn ($ods) system."""
    def __init__(self, planet_id: str, x: int, y: int):
        self.planet_id = planet_id
        self.x = x
        self.y = y
        self.key = f"{planet_id}-{x}-{y}-0"
        self.spawn_time = time.time()
        
        # Deterministic object id resembling LambdaMOO (#121157)
        self.objid = f"#{10000 + (pseudo_hash(planet_id, x, y, 999) % 899999)}"

        planet = PLANETS[planet_id]
        # Terrain is a deterministic property of the planet coordinate, not
        # of the lifetime of its temporary on-demand room object.
        self.biome_key = biome_at(planet_id, x, y)
        self.biome = BIOMES[self.biome_key]

        # Room title
        h_name = pseudo_hash(planet_id, x, y, 101)
        name_pool = ROOM_NAMES_BY_BIOME.get(self.biome_key, ["mysterious expanse"])
        self.name = name_pool[h_name % len(name_pool)]

        # Generate descriptive sentences matching Wayfar 1444
        self.sentences: List[str] = []
        h_flora = pseudo_hash(planet_id, x, y, 202)
        h_geo = pseudo_hash(planet_id, x, y, 303)
        h_therm = pseudo_hash(planet_id, x, y, 404)
        h_water = pseudo_hash(planet_id, x, y, 505)

        if self.biome_key in ("forest", "grassland", "marsh", "desert"):
            self.sentences.append(DESCRIPTIONS_FLORA[h_flora % len(DESCRIPTIONS_FLORA)])
            if (h_flora >> 2) % 2 == 0:
                self.sentences.append(DESCRIPTIONS_FLORA[(h_flora + 3) % len(DESCRIPTIONS_FLORA)])

        self.sentences.append(DESCRIPTIONS_GEOLOGY[h_geo % len(DESCRIPTIONS_GEOLOGY)])
        if (h_geo >> 1) % 2 == 0:
            self.sentences.append(DESCRIPTIONS_GEOLOGY[(h_geo + 2) % len(DESCRIPTIONS_GEOLOGY)])

        self.sentences.append(DESCRIPTIONS_THERMAL[h_therm % len(DESCRIPTIONS_THERMAL)])
        self.sentences.append(DESCRIPTIONS_WATER[h_water % len(DESCRIPTIONS_WATER)])

        # Creatures present
        self.creatures: List[str] = []
        h_critter = pseudo_hash(planet_id, x, y, 606)
        if (h_critter % 100) < 65:  # 65% chance of creatures
            c_pool = planet["creatures"]
            c1 = c_pool[h_critter % len(c_pool)]
            self.creatures.append(c1)
            if (h_critter % 100) < 30:
                c2 = c_pool[(h_critter + 1) % len(c_pool)]
                if c2 != c1:
                    self.creatures.append(c2)

        # Ground Items
        self.items: Dict[str, str] = {}
        h_item = pseudo_hash(planet_id, x, y, 707)
        if (h_item % 100) < 40:
            item_name = planet["items"][h_item % len(planet["items"])]
            self.items[item_name] = f"A salvageable {item_name} rests on the ground."

        self.sitting_users: Dict[Any, str] = {}


class OnDemandSystem:
    """
    On-Demand Room System ($ODS).
    Only stores and generates rooms when players occupy them.
    """
    def __init__(self):
        self.spawned_rooms: Dict[str, Room] = {}

    def get_room(self, planet_id: str, x: int, y: int) -> Room:
        # Wrap coordinates within 100x100
        x = x % 100
        y = y % 100
        key = f"{planet_id}-{x}-{y}-0"
        if key in self.spawned_rooms:
            return self.spawned_rooms[key]

        room = Room(planet_id, x, y)
        self.spawned_rooms[key] = room
        return room

    def cleanup_empty_rooms(self, active_coords: List[Tuple[str, int, int]]):
        """Discards rooms with no players to save memory, matching $halfhourly:clean_ods."""
        active_keys = {f"{p}-{x % 100}-{y % 100}-0" for p, x, y in active_coords}
        now = time.time()
        to_delete = []
        for key, room in self.spawned_rooms.items():
            if key not in active_keys and (now - room.spawn_time) > 300:  # Keep for 5 minutes
                to_delete.append(key)
        for key in to_delete:
            del self.spawned_rooms[key]

    def get_status_report(self) -> str:
        """
        Renders the exact $ODS Status display matching the screenshot.
        """
        areas: Dict[str, List[Room]] = {}
        for room in self.spawned_rooms.values():
            areas.setdefault(room.planet_id, []).append(room)

        lines = [
            f"{FG_CYAN}on demand spawn system{RESET}",
            "      ======",
            f"{BOLD}$ODS Status{RESET}",
            "      ======",
            f"There are {len(areas)} active on demand areas."
        ]

        now = time.time()
        for planet_id, r_list in areas.items():
            lines.append(f"{BOLD}Area: {planet_id}{RESET}")
            if len(r_list) > 6:
                lines.append(f" - {len(r_list)} rooms currently spawned")
            else:
                for r in r_list:
                    age_seconds = int(now - r.spawn_time)
                    if age_seconds < 60:
                        age_str = f"{age_seconds}s ago"
                    elif age_seconds < 3600:
                        age_str = f"{age_seconds // 60}m ago"
                    else:
                        age_str = f"{age_seconds // 3600}h ago"
                    lines.append(f" - {FG_YELLOW}{r.name}{RESET} [{r.objid}] (spawned {age_str})")

        lines.append("      ======")
        return "\n".join(lines)


# Global ODS instance
ods = OnDemandSystem()


def render_viewport_map(planet_id: str, center_x: int, center_y: int,
                        width_tiles: int = 17, height_tiles: int = 13) -> List[str]:
    """
    Renders the tactical 2-character per tile ANSI map around the player.
    Center tile is marked with '()' for the player.
    """
    planet = PLANETS[planet_id]
    biome_list = planet["biomes"]
    half_w = width_tiles // 2
    half_h = height_tiles // 2

    map_rows = []

    for dy in range(-half_h, half_h + 1):
        row_str = ""
        for dx in range(-half_w, half_w + 1):
            world_x = (center_x + dx) % 100
            world_y = (center_y + dy) % 100

            # Determine biome for tile
            b_info = BIOMES[biome_at(planet_id, world_x, world_y)]

            # Center is the player marker
            if dx == 0 and dy == 0:
                # Authentic Wayfar player marker: ()
                row_str += f"{b_info['bg']}{BOLD}{FG_WHITE}(){RESET}"
            else:
                # Micro-feature character
                h_char = pseudo_hash(planet_id, world_x, world_y, 888)
                char_pair = b_info["char_options"][h_char % len(b_info["char_options"])]
                row_str += f"{b_info['bg']}{b_info['fg']}{char_pair}{RESET}"

        map_rows.append(row_str)

    return map_rows


def format_side_by_side(map_rows: List[str], room: Room,
                        nickname: str, other_people: List[str]) -> str:
    """
    Aligns the map on the left and the room description on the right, matching the reference images.
    """
    # Build the right-side text column lines
    text_lines = []

    # 1. Room Title & Coordinates: choking canyon [30, 62 in or on MO-52]
    header = f"{BOLD}{FG_YELLOW}{room.name}{RESET} [{room.x}, {room.y} in or on {room.planet_id}]"
    text_lines.append(header)

    # 2. Colored Biome Badge
    badge_bg = room.biome["bg"]
    badge_fg = BOLD + FG_WHITE if badge_bg != BG_WHITE else BOLD + FG_BLACK
    biome_badge = f"{badge_bg}{badge_fg} {room.biome_key} biome {RESET}"
    text_lines.append(biome_badge)

    # 3. Descriptive Sentences
    for sentence in room.sentences:
        text_lines.append(sentence)

    # Combine side-by-side
    combined_lines = []
    max_rows = max(len(map_rows), len(text_lines))

    for i in range(max_rows):
        map_part = map_rows[i] if i < len(map_rows) else " " * 34
        text_part = text_lines[i] if i < len(text_lines) else ""
        combined_lines.append(f"{map_part}  {text_part}")

    # Below Map Section
    footer_lines = []

    # Creatures line
    if room.creatures:
        if len(room.creatures) == 1:
            c_desc = f"A {room.creatures[0]} is standing here."
        else:
            c_desc = f"A {room.creatures[0]} and a {room.creatures[1]} are standing here."
        footer_lines.append(f"\n{BOLD}{c_desc}{RESET}")

    # Other players
    if other_people:
        footer_lines.append(f"{FG_YELLOW}People here: {', '.join(other_people)}.{RESET}")

    # Ground Items
    if room.items:
        footer_lines.append(f"{FG_CYAN}Items visible: {', '.join(room.items.keys())}.{RESET}")

    # Exits in Cyan bracket: [ Exits: northeast south northwest west southwest north southeast east ]
    exit_list = " ".join(CARDINAL_DIRECTIONS.keys())
    exits_formatted = f"{FG_CYAN}[ Exits: {RESET}{exit_list} {FG_CYAN}]{RESET}"
    footer_lines.append(exits_formatted)

    return "\n".join(combined_lines) + "\n" + "\n".join(footer_lines)
