import socket
import time
import random
from typing import Dict, Tuple, Set, Any
from world import (
    ods, PLANETS, CARDINAL_DIRECTIONS,
    render_viewport_map, format_side_by_side,
    RESET, BOLD, FG_CYAN, FG_YELLOW, FG_WHITE, FG_RED
)

# Server network settings
HOST = '127.0.0.1'
PORT = 60025

# Connected clients state
clients: Set[Tuple[str, int]] = set()
client_nicknames: Dict[Tuple[str, int], str] = {}
client_locations: Dict[Tuple[str, int], Tuple[str, int, int]] = {}  # addr -> (planet_id, x, y)
client_inventories: Dict[Tuple[str, int], Dict[str, str]] = {}
client_stacks: Dict[Tuple[str, int], Dict[str, int]] = {}
player_profiles: Dict[str, Dict[str, Any]] = {}

BACKGROUNDS = {
    "ranger": {"description": "Employed by a farming mega-corp, you are familiar with basic weapons.", "difficulty": "normal", "goal": "Defeat 100 wildlife on the surface of a planet.", "target": 100, "reward": 1},
    "fabricator": {"description": "You were a laborer in a world factory.", "difficulty": "normal", "goal": "Craft 25 products of quality 70 or better.", "target": 25, "reward": 1},
    "retiree": {"description": "You've finally decided to live the dream of owning your own land.", "difficulty": "normal", "goal": "Control 10 buildings.", "target": 10, "reward": 1},
    "student": {"description": "Fresh from space university, your goal is to experience something new and epic.", "difficulty": "normal", "goal": "Reroll from the cockpit of a starship in space.", "target": 1, "reward": 1},
    "lab tech": {"description": "Study artifacts at a laboratory terminal.", "difficulty": "normal", "goal": "Research 25 artifacts.", "target": 25, "reward": 2},
    "botanist": {"description": "A keen gardener who yearns to explore and discover botanical life.", "difficulty": "moderate", "goal": "Discover 15 undocumented botanical specimens.", "target": 15, "reward": 1, "skills": ("Heavy Tan", "Sightseer", "Developing Observation")},
    "hacker": {"description": "Hack ships, control pads, building AI, and other objects.", "difficulty": "unspecified", "goal": "Hack 25 objects.", "target": 25, "reward": 2, "unlock": 5},
}

# Manual recipes from the Wayfar crafting reference. Ingredients are kept
# deliberately compact for this lightweight engine; tool and output names are
# the in-world names from the reference.
RECIPES = {
    "colonial machete": ("basic crafting tool", {"inert metal fragment": 2, "native lumber": 1}, "melee weapon"),
    "wilder javelin": ("basic crafting tool", {"wood": 1, "fiber": 1}, "melee weapon"),
    "colonial rifle": ("equipment crafting tool", {"inert metal fragment": 1, "inert wiring": 1, "weak power emitter": 1}, "ranged weapon"),
    "cheap orgo-reaper": ("equipment crafting tool", {"inert metal fragment": 1, "fiber": 1}, "harvesting tool"),
    "atmo-thrasher condenser": ("equipment crafting tool", {"inert metal fragment": 1, "weak power emitter": 1}, "harvesting tool"),
    "q-osmose energy collector": ("equipment crafting tool", {"inert metal fragment": 1, "weak power emitter": 1}, "harvesting tool"),
    "terrain surveyor": ("equipment crafting tool", {"inert metal fragment": 1, "inert wiring": 1}, "special weapon"),
    "hide armor": ("equipment crafting tool", {"hide": 2, "fiber": 1}, "armour"),
    "equipment crafting tool": ("basic crafting tool", {"weak power emitter": 1, "solid-phase metal": 2}, "tool"),
    "structure crafting tool": ("basic crafting tool", {"wood": 2, "inert metal fragment": 1}, "tool"),
    "micro-bot crafting tool": ("equipment crafting tool", {"inert metal fragment": 1, "weak power emitter": 1}, "tool"),
    "defensive crafting tool": ("equipment crafting tool", {"inert metal fragment": 1, "inert block": 1}, "tool"),
    "chemistry tool": ("equipment crafting tool", {"inert block": 1, "fiber": 1}, "tool"),
    "food processor": ("equipment crafting tool", {"inert metal fragment": 1, "inert wiring": 1}, "tool"),
    "maker block": ("basic crafting tool", {"inert block": 2}, "tool"),
    "cooking fire": ("basic crafting tool", {"wood": 2, "inert block": 1}, "tool"),
    "insta-meat soup": ("food processor", {"meat": 1, "water": 1}, "food"),
    "weak power emitter": ("basic crafting tool", {"inert metal fragment": 1, "inert wiring": 1}, "component"),
    "inert casing": ("basic crafting tool", {"inert metal fragment": 1}, "component"),
    "inert block": ("basic crafting tool", {"inert metal fragment": 1}, "component"),
    "medium power emitter": ("equipment crafting tool", {"weak power emitter": 1, "inert wiring": 1}, "component"),
    "inert wiring": ("basic crafting tool", {"copper wire strand": 1}, "component"),
    "inert slug clip": ("equipment crafting tool", {"inert casing": 1, "inert metal fragment": 1}, "ammunition"),
    "fiber backpack": ("equipment crafting tool", {"fiber": 2}, "container"),
    "shipping container": ("structure crafting tool", {"inert block": 2, "inert metal fragment": 1}, "container"),
    "pre-fab shelter kit": ("structure crafting tool", {"wood": 2, "fiber": 1, "inert block": 1}, "pre-fab kit"),
    "wooden fishing rig": ("basic crafting tool", {"wood": 1, "fiber": 1}, "product"),
    "furb@home health injector": ("chemistry tool", {"fiber": 1, "water": 1}, "product"),
    "fungal salve": ("chemistry tool", {"fungal spores": 1, "water": 1}, "product"),
    "fibrous bandage": ("basic crafting tool", {"fiber": 2}, "product"),
    "primitive bandage": ("basic crafting tool", {"fiber": 1}, "product"),
    "sign": ("structure crafting tool", {"wood": 1}, "product"),
    "colonial assembly datapad": ("basic crafting tool", {"inert metal fragment": 1, "inert wiring": 1}, "tool"),
    "engineering tool": ("basic crafting tool", {"weak power emitter": 1, "inert metal fragment": 2}, "tool"),
    "structure crafting tool": ("basic crafting tool", {"weak power emitter": 1, "solid-phase metal": 4, "inert casing": 4}, "tool"),
    "defensive crafting tool": ("equipment crafting tool", {"weak power emitter": 1, "inert casing": 1}, "tool"),
    "advanced structure tool": ("structure crafting tool", {"inert beam": 1, "inert siding": 1, "medium structure base": 1}, "tool"),
    "component crafting tool": ("basic crafting tool", {"inert metal fragment": 2, "inert wiring": 1}, "tool"),
}

RESOURCE_BY_BIOME = {
    "forest": ("wood", "native lumber", "fiber", "hide", "fungal spores", "neuro-aligned fiber", "energy", "plant matter"),
    "grassland": ("fiber", "wood", "native lumber", "hide", "fungal spores", "neuro-aligned fiber", "energy", "plant matter"),
    "marsh": ("fiber", "water", "fungal spores", "plant matter", "energy"),
    "water": ("water", "fiber"),
    "desert": ("inert metal fragment", "inert block", "water", "sand", "energy"),
    "canyon": ("inert metal fragment", "inert block", "copper wire strand", "solid-phase metal", "responsive metal", "energy"),
    "rocky": ("inert metal fragment", "inert block", "copper wire strand", "solid-phase metal", "responsive metal", "energy"),
    "metallic_wasteland": ("inert metal fragment", "copper wire strand", "inert block", "solid-phase metal", "inert casing", "inert beam", "inert siding", "responsive metal", "energy", "blank IC chip"),
    "crystalline": ("water", "fungal spores", "inert block"),
}

EQUIPMENT_PRODUCTS = {
    "melee weapon": ("bolo machete", "shock baton", "laser whip"),
    "ranged weapon": ("m141 assault rifle", "recoilless AVK tube", "e34 laser blaster", "judge brand pistol", "inferno pistol", "maxi-melter", "colonial handgun", "colonial rifle", "colonial revolver"),
    "harvesting tool": ("slimfast organic collector", "landslide farming harvestor", "cheap orgo-reaper"),
    "special weapon": ("terrain surveyor", "e-med patch blaster", "hand-held mapping AI", "e-med broadbeam", "low-power hand miner"),
    "armour": ("padded EVA suit", "scrap armor", "scrap helmet", "salvage pants", "scrap boots", "smile-corp flight helmet", "turret gunner helmet", "smile-corp control gloves"),
    "tool": ("vehicle assembly station", "structure crafting tool", "micro-bot crafting tool", "maker block", "robotic fabrication table", "chemistry tool", "defensive crafting tool", "food processor", "advanced structure tool", "advanced equipment workstation", "basic crafting tool", "material processor", "component crafting tool", "electronics processor", "engineering tool"),
    "component": ("wooden stock", "tactical stock", "slugthrower mechanics", "barrel", "slimfast intake"),
    "ammunition": ("weapon cell", "plasma cell", "reactive gauss dart clip", "AVK insert", "solid alloy slug clip", "melta battery", "heavy inert slug magazine", "magnum slug clip"),
    "container": ("competence cabinet", "heavy fabric backpack"),
    "gadget": ("disposable oceanic apparatus", "assault jetpack", "rocket pack", "robot control hand-pad", "emergency teleporter"),
    "module": ("claratin vision visor",),
    "product": ("kodak flasher", "salt water fishing gear", "fibrous bandage", "fragmentation grenade", "colony beacon", "remote charge", "timed charge", "proximity charge", "LAM", "okama gamesphere"),
}
EQUIPMENT_INGREDIENTS = {
    "melee weapon": {"inert metal fragment": 1, "inert wiring": 1},
    "ranged weapon": {"inert metal fragment": 1, "weak power emitter": 1},
    "harvesting tool": {"inert metal fragment": 1, "fiber": 1},
    "special weapon": {"weak power emitter": 1, "inert wiring": 1},
    "armour": {"hide": 1, "fiber": 1},
    "tool": {"inert metal fragment": 1, "inert wiring": 1},
    "component": {"inert metal fragment": 1, "inert wiring": 1},
    "ammunition": {"inert metal fragment": 1, "inert wiring": 1},
    "container": {"fiber": 2},
    "gadget": {"weak power emitter": 1, "inert wiring": 1},
    "module": {"weak power emitter": 1, "fiber": 1},
    "product": {"fiber": 1, "inert metal fragment": 1},
}

for equipment_category, products in EQUIPMENT_PRODUCTS.items():
    for equipment_product in products:
        RECIPES.setdefault(equipment_product, ("equipment crafting tool", EQUIPMENT_INGREDIENTS[equipment_category], equipment_category))

ENGINEERING_PRODUCTS = {
    "tool": ("experimental starship assembly tool",),
    "product": (
        "lifesign analyzer station", "machine gun nest", "automated material processor",
        "automated starship assembler", "automated equipment assembler", "structure demolition charge",
        "kerkove regen-matrix", "automated electronics processor", "automated industrial processor",
        "remote control handpad",
    ),
}
ENGINEERING_INGREDIENTS = {
    "tool": {"inert metal fragment": 1, "inert wiring": 1},
    "product": {"inert metal fragment": 1, "weak power emitter": 1},
}
for engineering_category, products in ENGINEERING_PRODUCTS.items():
    for engineering_product in products:
        RECIPES.setdefault(engineering_product, ("engineering tool", ENGINEERING_INGREDIENTS[engineering_category], engineering_category))

STRUCTURE_PRODUCTS = {
    "tool": ("material processor",),
    "component": ("inert beam", "inert siding", "simple structure base", "structure power core", "domestic grade building AI", "light structure base", "inert frame", "medium structure base"),
    "automated harvester": ("low-tech lumber yard", "automated mining plant", "solar energy collector", "geo/radiothermal power plant", "electromagnetic field collector"),
    "building": ("garage", "helo pad", "factory", "trash compactor", "commerce outlet", "racetrack", "machine arena", "rec dome", "sector center", "holo-theater", "emergency clinic", "small turret", "medium turret", "heavy turret", "cantina", "starship complex", "small warehouse", "chop shop", "infirmary", "dockhouse", "militia barracks", "hangar", "hostel", "laboratory", "refinery", "chapel", "agriculture pod", "stockpile warehouse"),
    "container": ("closet", "resource locker", "metal locker"),
    "product": ("solo artist stage", "shuttle terminal"),
}
DEFENSIVE_PRODUCTS = {
    "building": ("small turret", "medium turret", "heavy turret"),
    "gadget": ("ineffecient close combat shield", "energy reflux reactive shield", "bullet-shield reactive healing unit", "biowatch reactive healing unit", "host stabilization reactive unit"),
    "module": ("rotating laser turret", "scout-class rat gatler", "mobile SRM package", "simplex vehicle lock", "robo-terrier vehicle lock", "v-tite vehicle lock", "jungle cat electronic protection system", "shield-tek vehicle lock", "rabid dorg electronic protection system", "elite-tek vehicle lock"),
}
ADVANCED_STRUCTURE_PRODUCTS = {
    "component": ("lumber siding", "composite beam", "composite siding"),
    "automated harvester": ("electromagnetic field collector",),
    "building": ("colonial ranch", "faction headquarters", "fortified redoubt", "shelter bunker", "organic processing plant", "large warehouse", "nuclear enrichment plant"),
    "container": ("fishbowl", "small fishtank", "stylish fishtank", "huge fishtank"),
    "product": ("remote control button", "plastiform table", "comfy couch"),
}
COMPONENT_PRODUCTS = {
    "melee weapon": ("colonial machete",), "ranged weapon": ("colonial rifle",),
    "harvesting tool": ("cheap orgo-reaper", "atmo-thrasher condenser", "q-osmose energy collector"),
    "special weapon": ("low-power hand miner", "terrain surveyor"), "armour": ("hide armor",),
    "tool": ("equipment crafting tool", "structure crafting tool", "micro-bot crafting tool", "defensive crafting tool", "chemistry tool", "food processor", "maker block", "cooking fire"),
    "food": ("insta-meat soup",),
    "component": ("weak power emitter", "inert casing", "inert block", "medium power emitter", "domestic maker AI", "heavy power emitter", "homebrew logical AI", "homebrew defensive AI", "industrial grade maker AI", "empty nanobot can", "inert wiring"),
    "ammunition": ("inert slug clip",), "container": ("fiber backpack",), "pre-fab kit": ("pre-fab shelter kit",),
    "product": ("fragmentation grenade", "wooden fishing rig", "furb@home health injector", "fungal salve", "fibrous bandage", "primitive bandage"),
}

def register_tool_catalog(catalog: Dict[str, Tuple[str, ...]], tool_name: str, ingredients: Dict[str, int]):
    for category, products in catalog.items():
        for product in products:
            RECIPES.setdefault(product, (tool_name, ingredients, category))

register_tool_catalog(STRUCTURE_PRODUCTS, "structure crafting tool", {"inert metal fragment": 1, "inert block": 1})
register_tool_catalog(DEFENSIVE_PRODUCTS, "defensive crafting tool", {"inert metal fragment": 1, "weak power emitter": 1})
register_tool_catalog(ADVANCED_STRUCTURE_PRODUCTS, "advanced structure tool", {"inert beam": 1, "inert siding": 1})
register_tool_catalog(COMPONENT_PRODUCTS, "component crafting tool", {"inert metal fragment": 1, "inert wiring": 1})

# Exact recipes and project complexity supplied for these items. The game uses
# "inert metal fragment" as its inventory name for the documentation's inert metal.
EXACT_RECIPES = {
    "material processor": ("structure crafting tool", {"weak power emitter": 3, "solid-phase metal": 4, "inert casing": 4}, "tool", 20.0),
    "inert beam": ("material processor", {"inert metal": 3}, "component", 5.0),
    "inert siding": ("material processor", {"inert metal": 2}, "component", None),
    "simple structure base": ("material processor", {"native lumber": 8, "inert metal": 4}, "component", 25.0),
    "structure power core": ("material processor", {"weak power emitter": 1, "inert metal": 8, "any energy": 5}, "component", 30.0),
    "domestic grade building AI": ("material processor", {"blank IC chip": 2, "neuro-aligned fiber": 2}, "component", 17.0),
    "light structure base": ("material processor", {"weak power emitter": 1, "solid-phase metal": 2}, "component", 10.0),
    "inert frame": ("material processor", {"inert metal": 4}, "component", 15.0),
    "medium structure base": ("material processor", {"inert metal": 10, "solid-phase alloy": 6}, "component", 50.0),
    "solid-phase alloy": ("material processor", {"inert metal": 1, "solid-phase metal": 2}, "component", 12.0),
    "weak power emitter": ("basic crafting tool", {"inert metal": 2, "any energy": 5}, "component", 10.0),
    "inert casing": ("basic crafting tool", {"inert metal": 2}, "component", 8.0),
    "automated mining plant": ("structure crafting tool", {"industrial coordinator AI": 1, "inert metal": 10, "inert beam": 4, "inert siding": 4, "solid-phase alloy": 8, "light structure base": 1, "structure power core": 2}, "building", 65.0),
    "factory": ("structure crafting tool", {"simple structure base": 2, "inert beam": 4, "inert siding": 6, "structure power core": 1}, "building", 28.0),
    "sector center": ("structure crafting tool", {"simple structure base": 2, "inert beam": 10, "inert siding": 8, "structure power core": 4}, "building", 85.0),
    "small warehouse": ("structure crafting tool", {"inert beam": 6, "inert siding": 8, "light structure base": 2, "structure power core": 1}, "building", 40.0),
    "laboratory": ("structure crafting tool", {"simple structure base": 2, "inert beam": 4, "inert siding": 6, "structure power core": 2}, "building", 55.0),
    "refinery": ("structure crafting tool", {"simple structure base": 2, "inert beam": 4, "inert siding": 6, "solid-phase metal": 6, "structure power core": 1}, "building", 38.0),
    "stockpile warehouse": ("structure crafting tool", {"homebrew logical AI": 1, "inert wiring": 4, "inert beam": 6, "inert siding": 8, "light structure base": 2, "structure power core": 1}, "building", 55.0),
}
for exact_name, (exact_tool, exact_ingredients, exact_category, exact_complexity) in EXACT_RECIPES.items():
    RECIPES[exact_name] = (exact_tool, exact_ingredients, exact_category)

MATERIAL_PRODUCTS = {
    "resource": ("alcohol", "polymer fiber", "mineral acids", "petroleum distillate"),
    "component": ("solid-phase alloy", "supermagnetic alloy", "ceramic plate", "reactive armor plate", "plastiform brick", "electronics-grade silica", "rare earth metal", "refined elastomer", "fiber cloth", "adaptive-phase fabric", "hardened leather", "plastiform mesh", "nano-fullerene wafer", "nano-cor wafer", "nano-silk fabric", "silk cloth", "polymer brick"),
}
for material_category, products in MATERIAL_PRODUCTS.items():
    for product in products:
        RECIPES.setdefault(product, ("material processor", {"inert metal fragment": 1, "fiber": 1}, material_category))

# Recipes not listed among the source's processor outputs remain available as
# data dependencies for the documented automated mining plant.
RECIPES["industrial coordinator AI"] = ("material processor", {"domestic grade building AI": 1, "electronics-grade silica": 1}, "component")

ALTERNATE_TOOLS: Dict[str, Set[str]] = {}
for catalog, catalog_tool in ((EQUIPMENT_PRODUCTS, "equipment crafting tool"), (ENGINEERING_PRODUCTS, "engineering tool"), (STRUCTURE_PRODUCTS, "structure crafting tool"), (DEFENSIVE_PRODUCTS, "defensive crafting tool"), (ADVANCED_STRUCTURE_PRODUCTS, "advanced structure tool"), (COMPONENT_PRODUCTS, "component crafting tool")):
    for catalog_products in catalog.values():
        for catalog_product in catalog_products:
            ALTERNATE_TOOLS.setdefault(catalog_product, set()).add(catalog_tool)

STRUCTURE_NAMES = {name for data in (STRUCTURE_PRODUCTS, ADVANCED_STRUCTURE_PRODUCTS, DEFENSIVE_PRODUCTS) for category, products in data.items() if category in ("building", "automated harvester") for name in products}
RECIPE_COMPLEXITY = {"equipment crafting tool": 10.0, "engineering tool": 10.0, "structure crafting tool": 15.0}
RECIPE_COMPLEXITY.update({name: data[3] for name, data in EXACT_RECIPES.items() if data[3] is not None})

MATERIAL_ALIASES = {"inert metal": "inert metal fragment", "any energy": "energy"}


def carried_quantity(address, material: str) -> int:
    canonical = MATERIAL_ALIASES.get(material, material)
    return client_stacks.get(address, {}).get(canonical, 0)


def consume_materials(address, ingredients: Dict[str, int]):
    inventory = client_inventories[address]
    stacks = client_stacks[address]
    for material, quantity in ingredients.items():
        name = MATERIAL_ALIASES.get(material, material)
        stacks[name] -= quantity
        if stacks[name] <= 0:
            stacks.pop(name)
            inventory.pop(name, None)

# Skill costs and prerequisites from the supplied Wayfar skill overview.
SKILL_GROUPS = {
    "Tech Weapons": [("Power Operation", 50, ()), ("Touchpanel Training", 100, ("Power Operation",)), ("Non-Standard Ammunition Experience", 150, ("Power Operation",)), ("Machine Spirit", 200, ("Power Operation", "Touchpanel Training", "Non-Standard Ammunition Experience"))],
    "Primitive Weapons": [("Knows Which End Hurts People", 50, ()), ("Self Defense Training", 100, ("Knows Which End Hurts People",)), ("Advanced Slashing and Shooting", 150, ("Knows Which End Hurts People",)), ("Land Warrior", 200, ("Knows Which End Hurts People", "Self Defense Training", "Advanced Slashing and Shooting"))],
    "Off-World Weapons": [("Public Murder License", 100, ("Non-Standard Ammunition Experience",)), ("Beam Gunnery School", 100, ("Public Murder License",)), ("War-Glove Adept", 100, ("Public Murder License",)), ("Professional Combatant", 200, ("Public Murder License", "Beam Gunnery School", "War-Glove Adept"))],
    "Primitive Assembly": [("Improvisation", 50, ()), ("Crude Planning", 100, ()), ("Better Materials", 150, ("Improvisation", "Crude Planning")), ("Crafter", 200, ("Improvisation", "Crude Planning", "Better Materials")), ("Artisan", 400, ("Crafter",))],
    "Tech Operation": [("Basic Shiftscreen Operation", 75, ()), ("Tech Practice", 75, ("Basic Shiftscreen Operation",)), ("Low-Data Interfacing", 150, ("Basic Shiftscreen Operation",)), ("Has Read A Few Manuals", 200, ("Basic Shiftscreen Operation", "Tech Practice", "Low-Data Interfacing"))],
    "Off-World Operation": [("Technology Buff", 75, ("Has Read A Few Manuals",)), ("Data Decryption", 75, ("Technology Buff",)), ("Data Interception", 150, ("Data Decryption",)), ("Off-World Expertise", 200, ("Technology Buff", "Data Decryption", "Data Interception")), ("Off-World Resource Extraction", 500, ("Off-World Expertise", "Void Piloting", "Starship Operation", "Starship Engineering"))],
    "Security": [("Matrix Coder", 75, ("Low-Data Interfacing",)), ("Novice Hacker", 75, ("Matrix Coder",)), ("System Repurposing", 150, ("Novice Hacker",)), ("Data Pro", 200, ("System Repurposing",))],
    "Medicine": [("First Aid", 50, ()), ("Pharmacy", 100, ("First Aid",)), ("Neurosurgeon", 150, ("First Aid",)), ("Xenomedicine", 200, ("First Aid", "Pharmacy", "Neurosurgeon"))],
    "Exploration": [("Sightseer", 25, ()), ("Developing Observation", 75, ("Sightseer",)), ("Terrain Details", 150, ("Developing Observation",)), ("Unpaid Cartographer", 250, ("Sightseer", "Developing Observation", "Terrain Details"))],
    "Tech Assembly": [("Zoning License", 50, ("Crafter",)), ("Factory Operation", 100, ("Zoning License",)), ("Line Management", 150, ("Zoning License",)), ("Quality Control", 200, ("Zoning License", "Factory Operation", "Line Management"))],
    "Off-World Assembly": [("Schematic Mastery", 75, ("Quality Control",)), ("Advanced Assembly Platforms", 75, ("Schematic Mastery",)), ("Particle Recombination", 150, ("Schematic Mastery",)), ("Nanofactory Baron", 200, ("Schematic Mastery", "Advanced Assembly Platforms", "Particle Recombination"))],
    "Science": [("Lab Operation", 150, ()), ("Research Focus", 150, ("Lab Operation",)), ("Experimental Process", 100, ("Lab Operation",)), ("Multidisciplinarian", 100, ("Lab Operation", "Research Focus", "Experimental Process"))],
    "Vehicles": [("Driving", 100, ()), ("Flying", 100, ()), ("Expert Control Operation", 150, ("Driving", "Flying")), ("Experienced Pilot", 150, ("Expert Control Operation",))],
    "Cunning": [("Underhanded", 125, ()), ("Shadow Fiend", 125, ("Underhanded",)), ("Under the Radar", 125, ("Underhanded",)), ("Ghost Profile", 125, ("Underhanded", "Shadow Fiend", "Under the Radar"))],
    "Survival": [("Heavy Tan", 75, ()), ("Situational Awareness", 75, ()), ("I Work Out", 100, ("Heavy Tan",)), ("Tough Guy", 250, ("Heavy Tan", "Situational Awareness", "I Work Out")), ("Strong Back", 100, ()), ("Packrat", 100, ())],
    "Social": [("Theology", 250, ()), ("Musician", 500, ()), ("Consultant", 500, ())],
    "Economics": [("negotiation", 100, ()), ("supply expert", 200, ("negotiation",))],
    "Starships": [("Void Gunnery", 100, ("Technology Buff",)), ("Starship Operation", 100, ()), ("Void Piloting", 100, ("Starship Operation",)), ("Starship Command", 200, ("Void Piloting", "Starship Operation", "Void Gunnery")), ("Starship Engineering", 250, ("Starship Operation",)), ("Starship Repair", 250, ("Starship Operation",)), ("EVA Specialization", 250, ("Starship Operation",)), ("Void Data Analyst", 250, ("Starship Operation", "Data Decryption"))],
}
SKILLS = {skill.lower(): {"name": skill, "group": group, "cost": cost, "requires": requires} for group, entries in SKILL_GROUPS.items() for skill, cost, requires in entries}


def get_profile(nickname: str) -> Dict[str, Any]:
    return player_profiles.setdefault(nickname, {"background": None, "progress": 0, "reroll_points": 0, "completed": set(), "wildlife_kills": 0, "crafted_count": 0, "buildings": [], "skills": set(), "skill_points": 0, "skill_point_cap": 2500})


def award_skillpoints(nickname: str, amount: int):
    profile = get_profile(nickname)
    profile["skill_points"] = min(profile["skill_point_cap"], profile["skill_points"] + amount)


def update_background_progress(nickname: str, event: str, amount: int = 1) -> str:
    profile = get_profile(nickname)
    name = profile["background"]
    if not name or name in profile["completed"] or (name == "ranger" and event != "wildlife_kill"):
        return ""
    if name == "ranger":
        profile["wildlife_kills"] += amount
        profile["progress"] = profile["wildlife_kills"]
    else:
        return ""
    bg = BACKGROUNDS[name]
    if profile["progress"] >= bg["target"]:
        profile["completed"].add(name)
        profile["reroll_points"] += bg["reward"]
        return f"\nBackground complete: {name.title()}! You earned {bg['reward']} reroll point(s)."
    return f"\n{name.title()} progress: {profile['progress']}/{bg['target']}."

DEFAULT_PLANET = "WY-1444"


def broadcast_to_room(message: str, planet_id: str, x: int, y: int,
                      server_socket: socket.socket, exclude_address=None):
    """Sends a message to all players at the specified coordinates."""
    target_coord = (planet_id, x % 100, y % 100)
    for addr, loc in client_locations.items():
        if loc == target_coord and addr != exclude_address:
            try:
                server_socket.sendto(message.encode('utf-8'), addr)
            except OSError:
                pass


def send_look(address: Tuple[str, int], server_socket: socket.socket):
    """Generates the tactical map and side-by-side room description for a client."""
    planet_id, x, y = client_locations[address]
    room = ods.get_room(planet_id, x, y)

    # Gather other occupants
    other_people = []
    for addr, loc in client_locations.items():
        if loc == (planet_id, x, y) and addr != address:
            other_people.append(client_nicknames.get(addr, "Unknown"))

    nickname = client_nicknames.get(address, "Traveler")
    map_rows = render_viewport_map(planet_id, x, y, width_tiles=17, height_tiles=13)
    display_output = format_side_by_side(map_rows, room, nickname, other_people)

    server_socket.sendto(display_output.encode('utf-8'), address)


def handle_new_client(address: Tuple[str, int], server_socket: socket.socket):
    clients.add(address)
    start_x, start_y = PLANETS[DEFAULT_PLANET]["start_pos"]
    client_locations[address] = (DEFAULT_PLANET, start_x, start_y)
    client_inventories[address] = {
        "basic crafting tool": "A compact hand tool for simple manual recipes.",
        "colonial assembly datapad": "A reference datapad containing common recipes.",
        "wood": "A usable piece of salvaged wood.",
        "fiber": "A bundle of tough plant fiber.",
        "inert metal fragment": "A salvageable inert metal fragment.",
        "copper wire strand": "A length of copper wire.",
    }
    client_stacks[address] = {name: 1 for name in client_inventories[address]}

    welcome = (
        f"{BOLD}{FG_CYAN}=== Welcome to Wayfar 1444 ==={RESET}\n"
        f"You awaken on {BOLD}{DEFAULT_PLANET}{RESET}.\n"
        f"Type {BOLD}help{RESET} for commands, {BOLD}background{RESET} for character paths, or {BOLD}l{RESET} to look.\n"
    )
    server_socket.sendto(welcome.encode('utf-8'), address)
    send_look(address, server_socket)


def handle_disconnect(address: Tuple[str, int], server_socket: socket.socket):
    if address in clients:
        nickname = client_nicknames.get(address, "A traveler")
        planet_id, x, y = client_locations.get(address, (DEFAULT_PLANET, 0, 0))
        clients.remove(address)
        client_locations.pop(address, None)
        client_nicknames.pop(address, None)
        client_inventories.pop(address, None)
        client_stacks.pop(address, None)

        broadcast_to_room(
            f"--- {nickname} has departed into the void. ---",
            planet_id, x, y, server_socket
        )


def process_command(address: Tuple[str, int], raw_message: str, server_socket: socket.socket):
    current_loc = client_locations.get(address)
    if not current_loc:
        return
    planet_id, x, y = current_loc
    room = ods.get_room(planet_id, x, y)

    parts = raw_message.strip().split()
    if not parts:
        return

    # First word is command
    cmd = parts[0].lower()

    # Join announcements
    if raw_message.startswith("--- ") and raw_message.endswith(" has joined the chat ---"):
        nick = raw_message.split("--- ")[1].split(" has joined")[0].strip()
        client_nicknames[address] = nick
        broadcast_to_room(f"--- {nick} materializes at these coordinates. ---",
                          planet_id, x, y, server_socket, exclude_address=address)
        return

    # Normal chat (e.g. Nick: message)
    if cmd.endswith(":"):
        broadcast_to_room(raw_message, planet_id, x, y, server_socket)
        return

    # Extract command arguments and nickname suffix (client protocol: `cmd [args] nickname`)
    nickname = client_nicknames.get(address, "Traveler")
    args = parts[1:]
    if args and args[-1] == nickname:
        args = args[:-1]

    if cmd == "score":
        profile = get_profile(nickname)
        skills = sorted(profile["skills"])
        response = f"Skill points: {profile['skill_points']}/{profile['skill_point_cap']}\nSkills learned: {', '.join(skills) if skills else 'none'}\nReroll points: {profile['reroll_points']}"
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd in ("skills", "skill"):
        query = " ".join(args).strip().lower()
        profile = get_profile(nickname)
        if not query:
            response = "Skill groups: " + ", ".join(SKILL_GROUPS) + "\nUse 'skills <group>' or 'skills <skill name>' to inspect; 'learn <skill name>' to purchase."
        elif query in SKILLS:
            skill = SKILLS[query]
            prereqs = ", ".join(skill["requires"]) if skill["requires"] else "none"
            state = "learned" if skill["name"] in profile["skills"] else "not learned"
            response = f"{skill['name']} ({skill['group']})\nCost: {skill['cost']} skillpoints\nPrerequisites: {prereqs}\nStatus: {state}"
        else:
            group = next((name for name in SKILL_GROUPS if name.lower() == query), None)
            if group:
                response = group + ":\n" + "\n".join(f" - {name} ({cost})" for name, cost, _ in SKILL_GROUPS[group])
            else:
                response = "Unknown skill or group. Use 'skills' to list groups."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd == "learn":
        skill_name = " ".join(args).strip().lower()
        profile = get_profile(nickname)
        skill = SKILLS.get(skill_name)
        if not skill:
            response = "Unknown skill. Use 'skills' to browse skill groups."
        elif skill["name"] in profile["skills"]:
            response = f"You already know {skill['name']}."
        else:
            missing = [required for required in skill["requires"] if required not in profile["skills"]]
            if missing:
                response = "Prerequisites not met: " + ", ".join(missing) + "."
            elif profile["skill_points"] < skill["cost"]:
                response = f"You need {skill['cost']} skillpoints to learn {skill['name']}; you have {profile['skill_points']}."
            else:
                profile["skill_points"] -= skill["cost"]
                profile["skills"].add(skill["name"])
                response = f"You learn {skill['name']} for {skill['cost']} skillpoints."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd in ("background", "backgrounds"):
        profile = get_profile(nickname)
        subcommand = args[0].lower() if args else "list"
        if subcommand in ("list", "help"):
            lines = ["Available backgrounds:"]
            for name, bg in BACKGROUNDS.items():
                locked = profile["reroll_points"] < bg.get("unlock", 0)
                state = f"locked ({bg['unlock']} reroll points required)" if locked else "available"
                lines.append(f" - {name.title()} [{state}]: {bg['goal']} Reward: {bg['reward']} reroll point(s).")
            lines.append("Use: background select <name> | background status")
            response = "\n".join(lines)
        elif subcommand == "status":
            selected = profile["background"]
            if selected:
                bg = BACKGROUNDS[selected]
                count = profile["progress"]
                progress = f"{count}/{bg['target']}" if selected != "student" else ("ready" if count else "0/1")
                response = f"Background: {selected.title()}\nObjective: {bg['goal']}\nProgress: {progress}\nReroll points: {profile['reroll_points']}"
                if "skills" in bg:
                    response += "\nStarting skills: " + ", ".join(bg["skills"])
            else:
                response = f"No background selected. Reroll points: {profile['reroll_points']}. Use 'background select <name>'."
        elif subcommand == "select":
            name = " ".join(args[1:]).lower()
            if name not in BACKGROUNDS:
                response = "Unknown background. Use 'background list' to see the available backgrounds."
            elif profile["reroll_points"] < BACKGROUNDS[name].get("unlock", 0):
                response = f"{name.title()} is locked until you have {BACKGROUNDS[name]['unlock']} reroll points."
            elif profile["background"] and profile["background"] not in profile["completed"]:
                response = f"Complete {profile['background'].title()} before selecting another background."
            else:
                profile["background"] = name
                profile["progress"] = 0
                profile["wildlife_kills"] = 0
                if name == "botanist":
                    profile["skills"].update(BACKGROUNDS[name]["skills"])
                bg = BACKGROUNDS[name]
                response = f"Background selected: {name.title()}\n{bg['description']}\nObjective: {bg['goal']}"
                if "skills" in bg:
                    response += "\nStarting skills: " + ", ".join(bg["skills"])
        else:
            response = "Use: background list | background select <name> | background status"
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd in ("datapad", "lookup"):
        query = " ".join(args).lower().strip()
        if not query:
            response = "Lookup what? Try 'datapad fabric' or 'datapad tool'."
        elif "colonial assembly datapad" not in client_inventories.get(address, {}):
            response = "You need a colonial assembly datapad to look up common recipes."
        else:
            matches = [(name, recipe) for name, recipe in RECIPES.items() if query in name or query in recipe[2] or query in recipe[0]]
            response = "Known recipes matching your query:" if matches else "The datapad has no matching common recipes. Found blueprints and improvised recipes are not indexed."
            for name, (tool, ingredients, category) in matches[:12]:
                tools = sorted({tool} | ALTERNATE_TOOLS.get(name, set()))
                tool_text = " or ".join(tools)
                response += f"\n - {name} ({category}): use {tool_text}; requires " + ", ".join(f"{count} {item}" for item, count in ingredients.items()) + "."
                if name in RECIPE_COMPLEXITY:
                    response += f" Complexity: {RECIPE_COMPLEXITY[name]:.1f}."
            if len(matches) > 12:
                response += f"\n{len(matches) - 12} more matches; use a more specific query."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd == "gather":
        resource_query = " ".join(args).lower().strip()
        resource_keys = [item for item in RESOURCE_BY_BIOME.get(room.biome_key, ()) if item not in room.items]
        match = next((item for item in resource_keys if not resource_query or resource_query in item), None)
        if match:
            client_inventories[address][match] = f"A gathered quantity of {match}."
            client_stacks[address][match] = client_stacks[address].get(match, 0) + 1
            server_socket.sendto(f"You gather {match} from the {room.biome_key} terrain.".encode("utf-8"), address)
        else:
            server_socket.sendto(f"You find no gatherable {resource_query or 'materials'} here. Try another biome or coordinate.".encode("utf-8"), address)
        return

    if cmd in ("build", "construct"):
        building = " ".join(args).lower().strip()
        recipe = RECIPES.get(building)
        profile = get_profile(nickname)
        if building not in STRUCTURE_NAMES:
            response = "That is not a listed building. Use the datapad to look up buildings."
        elif not recipe:
            response = f"You don't have a construction plan for {building}."
        else:
            required_tool, ingredients, _category = recipe
            structure_tools = {"structure crafting tool", "advanced structure tool", "defensive crafting tool"}
            available_tool = next((candidate for candidate in (structure_tools | ALTERNATE_TOOLS.get(building, set())) if candidate in client_inventories[address]), None)
            stacks = client_stacks[address]
            missing = [f"{count} {name}" for name, count in ingredients.items() if carried_quantity(address, name) < count]
            sector_count = sum(1 for item, _p, _x, _y in profile["buildings"] if item == "sector center")
            if building == "sector center" and sector_count >= 5:
                response = "You can control no more than five sector centers."
            elif not available_tool:
                response = "You need a structure, advanced structure, or defensive crafting tool to construct buildings."
            elif missing:
                response = "You need: " + ", ".join(missing) + "."
            else:
                consume_materials(address, ingredients)
                profile["buildings"].append((building, planet_id, x, y))
                award_skillpoints(nickname, 5)
                if building == "sector center":
                    room.items.setdefault("resource locker", "A resource locker stands in the central plaza.")
                response = f"You deploy the structure drone and construct a {building} at [{x}, {y}]."
                if profile.get("background") == "retiree" and "retiree" not in profile["completed"]:
                    profile["progress"] = len(profile["buildings"])
                    if profile["progress"] >= BACKGROUNDS["retiree"]["target"]:
                        profile["completed"].add("retiree")
                        profile["reroll_points"] += BACKGROUNDS["retiree"]["reward"]
                        response += " Retiree background complete! You earned 1 reroll point."
                    else:
                        response += f" Retiree progress: {profile['progress']}/10 buildings."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd == "craft":
        product = " ".join(args).lower().strip()
        recipe = RECIPES.get(product)
        inventory = client_inventories.get(address, {})
        if not product:
            response = "Craft what? Use 'datapad <query>' to find recipes."
        elif not recipe:
            response = f"You don't know a recipe for {product}. Try a broad datapad lookup."
        else:
            tool, ingredients, _category = recipe
            stacks = client_stacks[address]
            missing = [f"{count} {name}" for name, count in ingredients.items() if carried_quantity(address, name) < count]
            available_tool = next((candidate for candidate in {tool} | ALTERNATE_TOOLS.get(product, set()) if candidate in inventory), None)
            if not available_tool:
                response = f"You need a {tool} to craft {product}. Try the datapad for a recipe to make one."
            elif missing:
                response = "You need: " + ", ".join(missing) + ". Gather materials with 'gather' or loot them from the terrain."
            else:
                consume_materials(address, ingredients)
                inventory[product] = f"A hand-crafted {product}."
                stacks[product] = stacks.get(product, 0) + 1
                award_skillpoints(nickname, 2)
                quality = 75
                progress = ""
                if get_profile(nickname).get("background") == "fabricator":
                    profile = get_profile(nickname)
                    if quality >= 70:
                        profile["crafted_count"] += 1
                        profile["progress"] = profile["crafted_count"]
                        bg = BACKGROUNDS["fabricator"]
                        if profile["progress"] >= bg["target"]:
                            profile["completed"].add("fabricator")
                            profile["reroll_points"] += bg["reward"]
                            progress = f" Fabricator background complete! You earned {bg['reward']} reroll point."
                        else:
                            progress = f" Fabricator progress: {profile['progress']}/{bg['target']} products at quality 70+."
                complexity = f" (complexity {RECIPE_COMPLEXITY[product]:.1f})" if product in RECIPE_COMPLEXITY else ""
                response = f"You craft {product} with {available_tool}{complexity} (quality {quality})." + progress
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if cmd == "improvise":
        lower_args = [part.lower() for part in args]
        profile = get_profile(nickname)
        if "Improvisation" not in profile["skills"]:
            response = "You need the Improvisation skill to improvise recipes."
        elif not lower_args:
            candidates = []
            for name, (_tool, ingredients, _category) in RECIPES.items():
                if any(carried_quantity(address, material) >= count for material, count in ingredients.items()):
                    candidates.append(name)
            response = "Improvisable items based on your carried materials:\n" + ("\n".join(" - " + name for name in sorted(candidates)[:30]) if candidates else "No possible items found.")
        elif len(lower_args) >= 2 and lower_args[0] == "on":
            tool_name = " ".join(args[1:]).lower()
            if tool_name not in client_inventories[address]:
                response = f"You aren't carrying a {tool_name}."
            else:
                available = sorted(name for name, (tool, _ingredients, _category) in RECIPES.items() if tool_name == tool or tool_name in ALTERNATE_TOOLS.get(name, set()))
                response = f"Improvisation recipes for {tool_name}:\n" + ("\n".join(" - " + name for name in available) if available else "No recipes are known for that tool.")
        elif "on" not in lower_args:
            response = "Use 'improvise on <tool>' to list recipes, or 'improvise <product> on <tool>'."
        else:
            split_at = lower_args.index("on")
            product = " ".join(args[:split_at]).lower()
            tool_name = " ".join(args[split_at + 1:]).lower()
            recipe = RECIPES.get(product)
            if not recipe:
                response = f"You don't know how to improvise {product}."
            elif tool_name not in client_inventories[address] or (tool_name != recipe[0] and tool_name not in ALTERNATE_TOOLS.get(product, set())):
                response = f"The {tool_name} cannot be used to improvise {product}."
            else:
                missing = [name for name, count in recipe[1].items() if carried_quantity(address, name) < count]
                if missing:
                    response = "You need: " + ", ".join(missing) + "."
                elif random.random() < 0.25:
                    response = f"Your attempt to improvise {product} fails; the materials are ruined."
                    consume_materials(address, recipe[1])
                else:
                    consume_materials(address, recipe[1])
                    client_inventories[address][product] = f"An improvised {product}."
                    client_stacks[address][product] = client_stacks[address].get(product, 0) + 1
                    award_skillpoints(nickname, 2)
                    response = f"You successfully improvise {product} using the {tool_name}."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    # Direction Shorthands (8 cardinal directions)
    direction_map = {
        'n': 'north', 'north': 'north',
        'ne': 'northeast', 'northeast': 'northeast',
        'e': 'east', 'east': 'east',
        'se': 'southeast', 'southeast': 'southeast',
        's': 'south', 'south': 'south',
        'sw': 'southwest', 'southwest': 'southwest',
        'w': 'west', 'west': 'west',
        'nw': 'northwest', 'northwest': 'northwest'
    }

    # 1. 8-Way Movement
    if cmd in direction_map:
        cardinal = direction_map[cmd]
        dx, dy = CARDINAL_DIRECTIONS[cardinal]
        new_x = (x + dx) % 100
        new_y = (y + dy) % 100
        award_skillpoints(nickname, 1)

        # Announce departure
        broadcast_to_room(f"--- {nickname} leaves off to the {cardinal}. ---",
                          planet_id, x, y, server_socket, exclude_address=address)

        # Update location
        client_locations[address] = (planet_id, new_x, new_y)

        # Announce arrival
        broadcast_to_room(f"--- {nickname} arrives from the opposite horizon. ---",
                          planet_id, new_x, new_y, server_socket, exclude_address=address)

        send_look(address, server_socket)
        return

    # 2. Look Command
    if cmd in ('l', 'look'):
        if args:
            target = " ".join(args).lower()
            profile = get_profile(nickname)
            if target == "sector center" and any(item == target and p == planet_id and bx == x and by == y for item, p, bx, by in profile["buildings"]):
                response = ("A large, gray brutalist building with few windows. It administers tourism and citizenship.\n"
                            "Rooms: central plaza, governor's office, factorium district.\n"
                            "Commands: relax, citizens, govern, sectormap, construction, buildings, resources, colony, events, roll-call, collection, modules, labor.")
                server_socket.sendto(response.encode("utf-8"), address)
            elif target in room.items:
                server_socket.sendto(room.items[target].encode('utf-8'), address)
            elif target in [c.lower() for c in room.creatures]:
                server_socket.sendto(f"A wild {target}. It surveys the surroundings cautiously.".encode('utf-8'), address)
            else:
                server_socket.sendto(f"You don't see a '{target}' here.".encode('utf-8'), address)
        else:
            send_look(address, server_socket)
        return

    # 3. $ODS Status Command (On-Demand Room System)
    if cmd in ('$ods', 'ods'):
        report = ods.get_status_report()
        server_socket.sendto(report.encode('utf-8'), address)
        return

    # 4. Planets / Shuttle Travel Command
    if cmd in ('planets', 'shuttle', 'planet'):
        if args and cmd in ('shuttle', 'planet'):
            target_planet = args[0].upper()
            if target_planet in PLANETS:
                tx, ty = PLANETS[target_planet]["start_pos"]
                broadcast_to_room(f"--- {nickname} steps into a transport shuttle and launches off-world. ---",
                                  planet_id, x, y, server_socket, exclude_address=address)
                client_locations[address] = (target_planet, tx, ty)
                server_socket.sendto(f"Shuttle trajectory locked. Descending to {target_planet}...\n".encode('utf-8'), address)
                broadcast_to_room(f"--- A shuttle lands, and {nickname} steps out. ---",
                                  target_planet, tx, ty, server_socket, exclude_address=address)
                send_look(address, server_socket)
            else:
                server_socket.sendto(f"Unknown planetary designation: {target_planet}".encode('utf-8'), address)
        else:
            planet_list = "\n".join([f" - {p}: {data['theme']}" for p, data in PLANETS.items()])
            resp = f"Designated Planets:\n{planet_list}\nUsage: shuttle <planet_name>"
            server_socket.sendto(resp.encode('utf-8'), address)
        return

    # 5. Inventory and Items
    if cmd in ('i', 'inventory'):
        inv = client_inventories.get(address, {})
        if inv:
            stacks = client_stacks.get(address, {})
            items_str = ", ".join(f"{name} x{stacks.get(name, 1)}" if stacks.get(name, 1) > 1 else name for name in inv)
            server_socket.sendto(f"Carrying: {items_str}.".encode('utf-8'), address)
        else:
            server_socket.sendto("Your pack is currently empty.".encode('utf-8'), address)
        return

    if cmd == 'take':
        if args:
            item_name = " ".join(args).lower()
            matching_key = next((k for k in room.items if k.lower() == item_name), None)
            if matching_key:
                desc = room.items.pop(matching_key)
                client_inventories[address][matching_key] = desc
                client_stacks[address][matching_key] = client_stacks[address].get(matching_key, 0) + 1
                server_socket.sendto(f"You pick up the {matching_key}.".encode('utf-8'), address)
                broadcast_to_room(f"--- {nickname} takes the {matching_key}. ---",
                                  planet_id, x, y, server_socket, exclude_address=address)
            else:
                server_socket.sendto(f"There is no '{item_name}' here to pick up.".encode('utf-8'), address)
        else:
            server_socket.sendto("Take what?".encode('utf-8'), address)
        return

    if cmd == 'drop':
        if args:
            item_name = " ".join(args).lower()
            inv = client_inventories.get(address, {})
            matching_key = next((k for k in inv if k.lower() == item_name), None)
            if matching_key:
                desc = inv.pop(matching_key)
                count = client_stacks[address].get(matching_key, 1)
                if count > 1:
                    inv[matching_key] = desc
                    client_stacks[address][matching_key] = count - 1
                else:
                    client_stacks[address].pop(matching_key, None)
                room.items[matching_key] = desc
                server_socket.sendto(f"You drop the {matching_key} onto the terrain.".encode('utf-8'), address)
                broadcast_to_room(f"--- {nickname} drops a {matching_key}. ---",
                                  planet_id, x, y, server_socket, exclude_address=address)
            else:
                server_socket.sendto(f"You aren't holding a '{item_name}'.".encode('utf-8'), address)
        else:
            server_socket.sendto("Drop what?".encode('utf-8'), address)
        return

    # 6. Creature Interactions
    if cmd in ('pet', 'feed', 'attack'):
        if args:
            target = " ".join(args).lower()
            matching_critter = next((c for c in room.creatures if c.lower() == target), None)
            if matching_critter:
                if cmd == 'pet':
                    server_socket.sendto(f"You cautiously reach out and pet the {matching_critter}.".encode('utf-8'), address)
                    broadcast_to_room(f"--- {nickname} pets the {matching_critter}. ---",
                                      planet_id, x, y, server_socket, exclude_address=address)
                elif cmd == 'feed':
                    server_socket.sendto(f"You offer nutrient rations to the {matching_critter}.".encode('utf-8'), address)
                    broadcast_to_room(f"--- {nickname} feeds the {matching_critter}. ---",
                                      planet_id, x, y, server_socket, exclude_address=address)
                elif cmd == 'attack':
                    room.creatures.remove(matching_critter)
                    room.items[f"{matching_critter} remains"] = f"The remains of a {matching_critter} lie here."
                    room.items["meat"] = f"A portion of meat from the {matching_critter}."
                    room.items["hide"] = f"A usable hide from the {matching_critter}."
                    award_skillpoints(nickname, 5)
                    progress_msg = update_background_progress(nickname, "wildlife_kill")
                    server_socket.sendto(f"You defeat the {matching_critter}. Its remains can be looted.{progress_msg}".encode('utf-8'), address)
                    broadcast_to_room(f"--- {nickname} defeats the {matching_critter}. ---",
                                      planet_id, x, y, server_socket, exclude_address=address)
            else:
                server_socket.sendto(f"You do not see a '{target}' here to {cmd}.".encode('utf-8'), address)
        else:
            server_socket.sendto(f"{cmd.capitalize()} what?".encode('utf-8'), address)
        return

    # 7. Roleplay: Emote, Say, Sit
    if cmd in ('emote', ':'):
        action_text = " ".join(args)
        server_socket.sendto(f"You {action_text}".encode('utf-8'), address)
        broadcast_to_room(f"--- {nickname} {action_text} ---", planet_id, x, y, server_socket, exclude_address=address)
        return

    if cmd in ('say', "'"):
        speech = " ".join(args)
        broadcast_to_room(f"{nickname} says: \"{speech}\"", planet_id, x, y, server_socket)
        return

    if cmd == 'sit':
        target = " ".join(args) if args else "the earth"
        server_socket.sendto(f"You take a seat upon {target}.".encode('utf-8'), address)
        broadcast_to_room(f"--- {nickname} sits on {target}. ---", planet_id, x, y, server_socket, exclude_address=address)
        return

    if cmd in ("buildings", "sectormap", "resources", "colony"):
        profile = get_profile(nickname)
        if cmd == "buildings":
            owned = profile["buildings"]
            response = "Buildings you control:\n" + ("\n".join(f" - {name} at {p} [{bx}, {by}]" for name, p, bx, by in owned) if owned else " none")
        elif cmd == "sectormap":
            counts: Dict[Tuple[str, int, int], int] = {}
            for _name, p, bx, by in profile["buildings"]:
                counts[(p, bx, by)] = counts.get((p, bx, by), 0) + 1
            response = "Buildings per occupied tile:\n" + ("\n".join(f" - {p} [{bx}, {by}]: {count}" for (p, bx, by), count in counts.items()) if counts else " no structures")
        elif cmd == "resources":
            available = RESOURCE_BY_BIOME.get(room.biome_key, ())
            response = f"Local {room.biome_key} resources: " + (", ".join(available) if available else "none recorded")
        else:
            response = f"Colony readout: {len(profile['buildings'])} controlled buildings; civilian and economy simulation is not available."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    # 8. Help
    if cmd == 'help':
        help_msg = (
            f"{BOLD}Wayfar 1444 Command Index:{RESET}\n"
            f"  {FG_CYAN}Movement:{RESET} n, ne, e, se, s, sw, w, nw (8 cardinal directions)\n"
            f"  {FG_CYAN}Tactical Map:{RESET} l or look (re-renders viewport & room sentences)\n"
            f"  {FG_CYAN}Spawn Status:{RESET} $ods (displays active on demand rooms and cache)\n"
            f"  {FG_CYAN}Interplanetary:{RESET} planets, shuttle <planet_name>\n"
            f"  {FG_CYAN}Interaction:{RESET} look at <target>, take <item>, drop <item>, i (inventory)\n"
            f"  {FG_CYAN}Creatures:{RESET} pet <critter>, feed <critter>, attack <critter>\n"
            f"  {FG_CYAN}Backgrounds:{RESET} background list, background select <name>, background status\n"
            f"  {FG_CYAN}Skills:{RESET} score, skills [group or name], learn <skill name>\n"
            f"  {FG_CYAN}Improvisation:{RESET} improvise, improvise on <tool>, improvise <product> on <tool> (requires Improvisation skill)\n"
            f"  {FG_CYAN}Crafting:{RESET} craft <product>, build <building>, datapad <query>, gather [material]\n"
            f"  {FG_CYAN}Colony:{RESET} buildings, sectormap, resources, colony\n"
            f"  {FG_CYAN}Social:{RESET} say <text>, emote <action>, sit <item>, exit"
        )
        server_socket.sendto(help_msg.encode('utf-8'), address)
        return

    if cmd in ('exit', 'quit'):
        handle_disconnect(address, server_socket)
        return

    # Fallback
    server_socket.sendto(f"Unknown command: '{cmd}'. Type 'help' for instructions.".encode('utf-8'), address)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.setblocking(False)
        print(f"Wayfar 1444 UDP Server online on {HOST}:{PORT}")

        last_cleanup_time = time.time()

        while True:
            try:
                data, address = server_socket.recvfrom(2048)
                message = data.decode('utf-8', errors='ignore')

                if address not in clients:
                    handle_new_client(address, server_socket)

                process_command(address, message, server_socket)

            except BlockingIOError:
                pass
            except Exception as ex:
                print(f"Server exception: {ex}")

            # Periodic cleanup of unused spawned rooms ($ODS)
            now = time.time()
            if now - last_cleanup_time > 60:
                active_locations = list(client_locations.values())
                ods.cleanup_empty_rooms(active_locations)
                last_cleanup_time = now

            time.sleep(0.02)


if __name__ == '__main__':
    main()
