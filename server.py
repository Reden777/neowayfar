import socket
import time
import random
from typing import Dict, Tuple, Set, Any
from world import (
    ods, PLANETS, CARDINAL_DIRECTIONS,
    render_viewport_map, format_side_by_side,
    strip_ansi,
    RESET, BOLD, FG_CYAN, FG_YELLOW, FG_WHITE, FG_RED
)

# Server network settings
HOST = '127.0.0.1'
PORT = 60025

# Connected clients state
clients: Set[Tuple[str, int]] = set()
client_nicknames: Dict[Tuple[str, int], str] = {}
client_locations: Dict[Tuple[str, int], Tuple[str, int, int]] = {}  # addr -> (planet_id, x, y)
client_space_locations: Dict[Tuple[str, int], Tuple[int, int]] = {}  # addr -> orbital grid coordinates
timed_tool_actions: Dict[Tuple[str, int], Dict[str, Any]] = {}
client_inventories: Dict[Tuple[str, int], Dict[str, str]] = {}
client_stacks: Dict[Tuple[str, int], Dict[str, int]] = {}
client_container_contents: Dict[Tuple[str, int], Dict[str, Dict[str, int]]] = {}
player_profiles: Dict[str, Dict[str, Any]] = {}

BACKGROUNDS = {
    "ranger": {"description": "Employed by a farming mega-corp, you are familiar with basic weapons.", "difficulty": "normal", "goal": "Defeat 100 wildlife on the surface of a planet.", "target": 100, "reward": 1},
    "fabricator": {"description": "You were a laborer in a world factory.", "difficulty": "normal", "goal": "Craft 25 products of quality 70 or better.", "target": 25, "reward": 1},
    "retiree": {"description": "You've finally decided to live the dream of owning your own land.", "difficulty": "normal", "goal": "Control 10 buildings.", "target": 10, "reward": 1},
    "student": {"description": "Fresh from space university, your goal is to experience something new and epic.", "difficulty": "normal", "goal": "Reroll from the cockpit of a starship in space.", "target": 1, "reward": 1},
    "lab tech": {"description": "Study artifacts at a laboratory terminal.", "difficulty": "normal", "goal": "Research 25 artifacts.", "target": 25, "reward": 2},
    "botanist": {"description": "A keen gardener who yearns to explore and discover botanical life.", "difficulty": "moderate", "goal": "Discover 15 undocumented botanical specimens.", "target": 15, "reward": 1, "skills": ("Heavy Tan", "Sightseer", "Developing Observation")},
    "scavenger": {"description": "You seek abandoned planetary sites and the technology left behind.", "difficulty": "normal", "goal": "Scavenge 10 planetary points of interest.", "target": 10, "reward": 1},
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
    "atmo-thrasher condenser": ("equipment crafting tool", {"inert metal fragment": 2, "weak power emitter": 1}, "harvesting tool"),
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
    "underwater": ("water", "pressure-grown pearl", "bioluminescent spore", "alkali crust"),
    "forest": ("wood", "native lumber", "fiber", "hide", "fungal spores", "neuro-aligned fiber", "energy", "plant matter"),
    "jungle": ("native lumber", "native fiber", "fiber", "fungal spores", "neuro-aligned fiber", "adaptive-phase fiber", "plant matter", "hide", "energy"),
    "mountain": ("inert metal fragment", "inert block", "solid-phase metal", "solid-phase conduit", "solid-phase hull plate", "copper wire strand", "energy"),
    "fungal_zone": ("fungal spores", "volatile fungal spores", "native fiber", "adaptive-phase fiber", "fiber", "bioluminescent spore", "plant matter"),
    "volcanic": ("heat-resistant alloy nodule", "inert metal fragment", "solid-phase metal", "thermal kretherson", "energy", "fused silicate"),
    "pink_desert": ("rose quartz crystal", "pink silicate", "water", "energy", "sand"),
    "grassland": ("fiber", "wood", "native lumber", "hide", "fungal spores", "neuro-aligned fiber", "energy", "plant matter"),
    "marsh": ("fiber", "water", "fungal spores", "plant matter", "energy"),
    "water": ("water", "fiber"),
    "desert": ("inert metal fragment", "inert block", "water", "sand", "energy"),
    "canyon": ("inert metal fragment", "inert block", "copper wire strand", "solid-phase metal", "responsive metal", "energy"),
    "rocky": ("inert metal fragment", "inert block", "copper wire strand", "solid-phase metal", "responsive metal", "energy"),
    "metallic_wasteland": ("inert metal fragment", "copper wire strand", "inert block", "solid-phase metal", "solid-phase conduit", "inert casing", "inert beam", "inert siding", "responsive metal", "energy", "weak power emitter", "light starship power core", "weaponry power bank", "inert superstructure", "solid-phase hull plate", "light ion engine", "cargo bay", "blank IC chip"),
    "crystalline": ("water", "fungal spores", "inert block"),
    "water": ("water", "pressure-grown pearl", "bioluminescent spore", "alkali crust"),
}
RESOURCE_YIELD_BY_BIOME = {
    "forest": 5, "jungle": 7, "grassland": 4, "underwater": 3, "water": 3,
    "marsh": 4, "fungal_zone": 4, "desert": 2, "pink_desert": 2,
    "canyon": 3, "rocky": 3, "mountain": 2, "metallic_wasteland": 4,
    "volcanic": 2, "crystalline": 3,
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
RECIPE_COMPLEXITY["atmo-thrasher condenser"] = 10.0

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


def resolve_name(query: str, names):
    """Resolve a full or partial in-world name without silently picking ambiguity."""
    query = query.lower().strip()
    choices = list(names)
    exact = next((name for name in choices if name.lower() == query), None)
    if exact:
        return exact, None
    matches = [name for name in choices if query and query in name.lower()]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, "Which do you mean: " + ", ".join(matches[:8]) + "?"
    return None, None


def parse_amount_item(text: str):
    words = text.strip().split()
    amount = 1
    if words and words[0].isdigit():
        amount = max(1, int(words.pop(0)))
    elif words and words[0].lower() == "all":
        amount = None
        words.pop(0)
    return amount, " ".join(words).lower()

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
    return player_profiles.setdefault(nickname, {"background": None, "progress": 0, "reroll_points": 0, "completed": set(), "wildlife_kills": 0, "crafted_count": 0, "buildings": [], "skills": set(), "skill_points": 0, "skill_point_cap": 2500, "bigmap": False, "ansi": True, "health": 100, "scavenged_pois": set(), "ships": []})


SHIP_BLUEPRINTS = {
    "pioneer skiff": {"description": "A lightly equipped one-person planetary craft.", "ingredients": {"inert metal fragment": 4, "inert wiring": 2, "weak power emitter": 2}},
    "survey cutter": {"description": "A durable survey craft with room for equipment and supplies.", "ingredients": {"inert metal fragment": 8, "inert wiring": 4, "weak power emitter": 3, "solid-phase metal": 2}},
    "asteroid miner": {"description": "A lop-sided, blocky Central Complex budget ship built to exploit asteroid minerals. It is the only spacecraft that can fit a gas harvesting module.", "ingredients": {"solid-phase conduit": 2, "native fiber": 3, "energy": 17, "solid-phase metal": 1, "light starship power core": 1, "weak power emitter": 2, "inert metal fragment": 10, "inert wiring": 4, "weaponry power bank": 2, "responsive metal": 3, "inert casing": 2, "adaptive-phase fiber": 6, "inert superstructure": 1, "thermal kretherson": 5, "solid-phase hull plate": 4, "light ion engine": 1, "cargo bay": 1}},
}
SHIP_ASSEMBLY_TOOL = "experimental starship assembly tool"
RECIPES["asteroid miner"] = (SHIP_ASSEMBLY_TOOL, SHIP_BLUEPRINTS["asteroid miner"]["ingredients"], "starship")
RECIPES["gas harvesting module"] = ("engineering tool", {"weak power emitter": 2, "responsive metal": 1, "inert wiring": 2}, "starship module")


def ship_brief(ship: Dict[str, Any]) -> str:
    state = "in orbit" if ship.get("in_space") else "landed"
    return f"{ship['name'].title()} ({state})"


def award_skillpoints(nickname: str, amount: int):
    profile = get_profile(nickname)
    profile["skill_points"] = min(profile["skill_point_cap"], profile["skill_points"] + amount)


def update_background_progress(nickname: str, event: str, amount: int = 1) -> str:
    profile = get_profile(nickname)
    name = profile["background"]
    if not name or name in profile["completed"]:
        return ""
    if name == "ranger":
        if event != "wildlife_kill":
            return ""
        profile["wildlife_kills"] += amount
        profile["progress"] = profile["wildlife_kills"]
    elif name == "scavenger":
        if event != "poi_scavenge":
            return ""
        profile["progress"] += amount
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
    profile = get_profile(nickname)
    hazard_notice = ""
    hazard = room.biome.get("hazard")
    if hazard:
        visited = profile.setdefault("hazard_visits", set())
        visit_key = (planet_id, x, y)
        if visit_key not in visited:
            visited.add(visit_key)
            damage = random.randint(3, 7) if hazard == "spores" else random.randint(5, 12)
            profile["health"] = max(1, profile["health"] - damage)
            hazard_notice = f"\nHazard: {hazard.title()} exposure deals {damage} damage. Health: {profile['health']}/100."
    if room.poi_kind == "droid factory" and not room.poi_active and address in client_nicknames:
        room.poi_active = True
        for droid in room.hostile_droids:
            droid["active"] = True
        damage = random.randint(4, 10)
        profile["health"] = max(1, profile["health"] - damage)
        room.poi_alert = f"The sleeping droids wake and attack! You take {damage} damage. Health: {profile['health']}/100."
    bigmap = profile.get("bigmap", False)
    use_ansi = profile.get("ansi", True)
    size = 21 if bigmap else 17
    map_rows = render_viewport_map(planet_id, x, y, width_tiles=size, height_tiles=21 if bigmap else 13, use_ansi=use_ansi)
    display_output = format_side_by_side(map_rows, room, nickname, other_people)
    if not use_ansi:
        display_output = strip_ansi(display_output)
    display_output += f"\nHealth: {profile['health']}/100.{hazard_notice}"

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
    client_container_contents[address] = {}

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
        active_ship = next((item for item in get_profile(nickname).get("ships", []) if item.get("active")), None)
        if active_ship and address in client_space_locations:
            active_ship["in_space"] = False
            active_ship.pop("origin", None)
        clients.remove(address)
        client_locations.pop(address, None)
        client_space_locations.pop(address, None)
        timed_tool_actions.pop(address, None)
        client_nicknames.pop(address, None)
        client_inventories.pop(address, None)
        client_stacks.pop(address, None)
        client_container_contents.pop(address, None)

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
        send_look(address, server_socket)
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

    if cmd == "chat":
        message = " ".join(args).strip()
        if not message:
            server_socket.sendto(b"Chat what?", address)
        else:
            for recipient in list(clients):
                server_socket.sendto(f"[Chatnet] {nickname}: {message}".encode("utf-8"), recipient)
        return

    if cmd in ("ships", "ship", "board", "launch", "land", "fly"):
        profile = get_profile(nickname)
        ships = profile.setdefault("ships", [])
        subcommand = cmd if cmd != "ship" else (args[0].lower() if args else "list")
        ship_args = args if cmd != "ship" else args[1:]
        active = next((item for item in ships if item.get("active")), None)
        if subcommand in ("ships", "list"):
            response = "Your ships: " + (", ".join(ship_brief(item) for item in ships) if ships else "none")
            response += f"\nBlueprints: {', '.join(SHIP_BLUEPRINTS)}. Build: ship build <blueprint>."
        elif subcommand == "build":
            requested = " ".join(ship_args).lower().strip()
            blueprint = SHIP_BLUEPRINTS.get(requested)
            if not blueprint:
                response = f"Unknown ship blueprint. Available: {', '.join(SHIP_BLUEPRINTS)}."
            elif SHIP_ASSEMBLY_TOOL not in client_inventories.get(address, {}):
                response = f"You need an {SHIP_ASSEMBLY_TOOL} to assemble ships."
            else:
                missing = [f"{count} {name}" for name, count in blueprint["ingredients"].items() if carried_quantity(address, name) < count]
                if missing:
                    response = "You need: " + ", ".join(missing) + "."
                else:
                    consume_materials(address, blueprint["ingredients"])
                    ship = {"name": requested, "description": blueprint["description"], "active": not active, "in_space": False, "modules": []}
                    ships.append(ship)
                    award_skillpoints(nickname, 10)
                    response = f"The assembly tool finishes your {requested}." + (" It is now your active ship." if ship["active"] else " Board it with 'board <name>'.")
        elif subcommand == "board":
            target = " ".join(ship_args).lower().strip()
            ship = next((item for item in ships if item["name"] == target), None)
            if not ship:
                response = "You don't own that ship. Use 'ships' to list your fleet."
            elif address in client_space_locations:
                response = "You are already aboard a ship in orbit. Land first."
            else:
                for item in ships:
                    item["active"] = item is ship
                active = ship
                response = f"You board your {ship['name']}. {ship['description']}"
        elif subcommand == "fit":
            module = " ".join(ship_args).lower().strip()
            if not active:
                response = "You need to board one of your ships before fitting a module."
            elif address in client_space_locations:
                response = "Land your ship before fitting modules."
            elif module != "gas harvesting module":
                response = "Available ship module: gas harvesting module."
            elif active["name"] != "asteroid miner":
                response = "Only the Asteroid Miner has fittings for a gas harvesting module."
            elif module not in client_inventories.get(address, {}):
                response = "You need to carry a gas harvesting module to fit it. Craft one with 'craft gas harvesting module'."
            elif module in active.setdefault("modules", []):
                response = "Your Asteroid Miner already has a gas harvesting module fitted."
            else:
                consume_materials(address, {module: 1})
                active["modules"].append(module)
                response = "You fit the gas harvesting module to your Asteroid Miner. Launch and use 'ship harvest gas' to collect volatile gas."
        elif subcommand == "harvest":
            target = " ".join(ship_args).lower().strip()
            if target != "gas":
                response = "Use 'ship harvest gas' while in orbit."
            elif not active or active["name"] != "asteroid miner":
                response = "Only an Asteroid Miner can harvest gas."
            elif "gas harvesting module" not in active.get("modules", []):
                response = "Your Asteroid Miner needs a fitted gas harvesting module."
            elif address not in client_space_locations:
                response = "Launch into orbit before harvesting gas."
            else:
                inventory = client_inventories[address]
                stacks = client_stacks[address]
                inventory["volatile gas"] = "Volatile gas collected by a gas harvesting module."
                stacks["volatile gas"] = stacks.get("volatile gas", 0) + 1
                response = "The gas harvesting module draws a canister of volatile gas from the surrounding field."
        elif subcommand in ("launch", "fly", "land"):
            if not active:
                response = "You need an active ship. Use 'board <name>' or assemble one with 'ship build <blueprint>'."
            elif subcommand == "launch":
                if address in client_space_locations:
                    response = "Your ship is already in orbit."
                else:
                    client_space_locations[address] = (0, 0)
                    active["in_space"] = True
                    active["origin"] = client_locations.get(address, (planet_id, x, y))
                    response = f"You lift your {active['name']} into orbit above {planet_id}. Use 'fly <direction>' to maneuver or 'land' to return."
                    if profile.get("background") == "student" and "student" not in profile["completed"]:
                        profile["completed"].add("student")
                        profile["reroll_points"] += BACKGROUNDS["student"]["reward"]
                        response += " Student background complete! You earned 1 reroll point."
            elif subcommand == "land":
                if address not in client_space_locations:
                    response = "Your ship is already landed."
                else:
                    client_space_locations.pop(address, None)
                    active["in_space"] = False
                    origin = active.pop("origin", None)
                    if origin:
                        client_locations[address] = origin
                        planet_id, x, y = origin
                    response = f"Your {active['name']} lands on {planet_id}."
                    server_socket.sendto(response.encode("utf-8"), address)
                    send_look(address, server_socket)
                    return
            else:
                direction = " ".join(ship_args).lower().strip()
                deltas = {"n": (0, -1), "north": (0, -1), "ne": (1, -1), "northeast": (1, -1), "e": (1, 0), "east": (1, 0), "se": (1, 1), "southeast": (1, 1), "s": (0, 1), "south": (0, 1), "sw": (-1, 1), "southwest": (-1, 1), "w": (-1, 0), "west": (-1, 0), "nw": (-1, -1), "northwest": (-1, -1)}
                if address not in client_space_locations:
                    response = "Launch first before maneuvering in space."
                elif direction not in deltas:
                    response = "Use 'fly n|ne|e|se|s|sw|w|nw' to maneuver."
                else:
                    sx, sy = client_space_locations[address]
                    dx, dy = deltas[direction]
                    client_space_locations[address] = (sx + dx, sy + dy)
                    response = f"You pilot the {active['name']} to orbital coordinates [{sx + dx}, {sy + dy}]."
        else:
            response = "Ship commands: ships, ship build <blueprint>, board <name>, ship fit <module>, launch, fly <direction>, land, ship harvest gas."
        server_socket.sendto(response.encode("utf-8"), address)
        return

    if address in client_space_locations:
        server_socket.sendto(b"You are aboard your ship in orbit. Use 'fly <direction>' or 'land'.", address)
        return

    if cmd == "page":
        if len(args) < 2:
            server_socket.sendto(b"Usage: page <person name> <message>", address)
            return
        target_query = args[0].lower()
        recipients = [addr for addr, name in client_nicknames.items() if target_query in name.lower()]
        if len(recipients) != 1:
            response = "No logged-in person matches that name." if not recipients else "Which person do you mean?"
            server_socket.sendto(response.encode("utf-8"), address)
            return
        message = " ".join(args[1:])
        server_socket.sendto(f"[Page from {nickname}] {message}".encode("utf-8"), recipients[0])
        server_socket.sendto(f"You page {client_nicknames[recipients[0]]}: {message}".encode("utf-8"), address)
        return

    if cmd in ("map", "bigmap", "ansi", "blind"):
        profile = get_profile(nickname)
        value = " ".join(args).lower().strip()
        if cmd == "map" and value in ("big", "bigmap", "21x21"):
            profile["bigmap"] = True
        elif cmd == "map" and value in ("small", "normal", "17x13"):
            profile["bigmap"] = False
        elif cmd == "bigmap" and value in ("on", "yes", "true"):
            profile["bigmap"] = True
        elif cmd == "bigmap" and value in ("off", "no", "false"):
            profile["bigmap"] = False
        elif cmd == "bigmap" and value in ("toggle", ""):
            profile["bigmap"] = not profile["bigmap"]
        elif cmd == "ansi" and value in ("on", "yes", "true"):
            profile["ansi"] = True
        elif cmd == "ansi" and value in ("off", "no", "false"):
            profile["ansi"] = False
        elif cmd == "blind" and value in ("on", "yes", "true"):
            profile["ansi"] = False
        elif cmd == "blind" and value in ("off", "no", "false"):
            profile["ansi"] = True
        elif value:
            response = "Use map big|small, bigmap on|off|toggle, ansi on|off, or blind on|off."
            server_socket.sendto(response.encode("utf-8"), address)
            return
        response = f"Map preference: {'21x21' if profile['bigmap'] else '17x13'}; ANSI {'on' if profile['ansi'] else 'off'}."
        server_socket.sendto(response.encode("utf-8"), address)
        send_look(address, server_socket)
        return

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
        yield_limit = RESOURCE_YIELD_BY_BIOME.get(room.biome_key, 2)
        resource_keys = [item for item in RESOURCE_BY_BIOME.get(room.biome_key, ())
                         if room.resource_gathered.get(item, 0) < yield_limit
                         and (not resource_query or resource_query in item)]
        match = random.choice(resource_keys) if resource_keys else None
        if match:
            room.resource_gathered[match] = room.resource_gathered.get(match, 0) + 1
            client_inventories[address][match] = f"A gathered quantity of {match}."
            client_stacks[address][match] = client_stacks[address].get(match, 0) + 1
            remaining = max(0, yield_limit - room.resource_gathered[match])
            server_socket.sendto(f"You gather {match} from the {room.biome['name']} terrain ({remaining} more unit(s) of this resource available here).".encode("utf-8"), address)
        else:
            server_socket.sendto(f"You find no gatherable {resource_query or 'materials'} here. Try another biome or coordinate.".encode("utf-8"), address)
        return

    if cmd in ("harvest", "survey"):
        tool = "atmo-thrasher condenser"
        if tool not in client_inventories.get(address, {}):
            response = "You need an atmo-thrasher condenser. Craft one with an equipment crafting tool."
        elif address in client_space_locations:
            response = "The condenser needs a planetary atmosphere; land before using it."
        elif address in timed_tool_actions:
            response = "The condenser is already working."
        elif cmd == "harvest" and " ".join(args).lower().strip() not in ("", "water", "unpurified water"):
            response = "The atmo-thrasher condenser harvests unpurified water. Use 'harvest water'."
        else:
            duration = 5.0 if cmd == "harvest" else 10.0
            timed_tool_actions[address] = {
                "kind": cmd,
                "completes_at": time.time() + duration,
                "location": client_locations[address],
                "nickname": nickname,
            }
            if cmd == "harvest":
                response = "The atmo-thrasher condenser begins siphoning atmospheric moisture. One unit of unpurified water will be ready in 5.0 seconds; biological hazards may remain."
            else:
                response = "The atmo-thrasher condenser begins its 10.0-second survey."
        server_socket.sendto(response.encode("utf-8"), address)
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
        craft_args = " ".join(args).lower().strip()
        requested_tool = None
        if " on " in craft_args:
            craft_args, tool_query = craft_args.rsplit(" on ", 1)
            requested_tool, tool_error = resolve_name(tool_query, client_inventories.get(address, {}))
            if tool_error:
                server_socket.sendto(tool_error.encode("utf-8"), address)
                return
        product, product_error = resolve_name(craft_args, RECIPES)
        if product_error:
            server_socket.sendto(product_error.encode("utf-8"), address)
            return
        recipe = RECIPES.get(product) if product else None
        inventory = client_inventories.get(address, {})
        if not craft_args:
            response = "Craft what? Use 'datapad <query>' to find recipes."
        elif not recipe:
            response = f"You don't know a recipe for {product}. Try a broad datapad lookup."
        else:
            tool, ingredients, _category = recipe
            stacks = client_stacks[address]
            missing = [f"{count} {name}" for name, count in ingredients.items() if carried_quantity(address, name) < count]
            valid_tools = {tool} | ALTERNATE_TOOLS.get(product, set())
            available_tool = requested_tool if requested_tool in valid_tools else None
            if requested_tool and not available_tool:
                response = f"The {requested_tool} cannot craft {product}."
                server_socket.sendto(response.encode("utf-8"), address)
                return
            if not requested_tool:
                available_tool = next((candidate for candidate in valid_tools if candidate in inventory), None)
            if not available_tool:
                response = f"You need a {tool} to craft {product}. Try the datapad for a recipe to make one."
            elif missing:
                response = "You need: " + ", ".join(missing) + ". Gather materials with 'gather' or loot them from the terrain."
            else:
                consume_materials(address, ingredients)
                crafted_ship = product in SHIP_BLUEPRINTS
                if crafted_ship:
                    profile = get_profile(nickname)
                    active_ship = next((item for item in profile.setdefault("ships", []) if item.get("active")), None)
                    ship = {"name": product, "description": SHIP_BLUEPRINTS[product]["description"], "active": not active_ship, "in_space": False, "modules": []}
                    profile["ships"].append(ship)
                else:
                    if product == "atmo-thrasher condenser":
                        inventory[product] = ("A small transparent canteen-shaped atmospheric condenser. It forms thin bladders of unpurified water; biological hazards may remain. Use 'harvest water' or 'survey'.")
                    else:
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
                if crafted_ship:
                    response = f"You craft the {product} with {available_tool}{complexity}. It is added to your fleet." + (" It is now your active ship." if ship["active"] else " Board it with 'board asteroid miner'.") + progress
                else:
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
            if target.startswith("at "):
                target = target[3:]
            look_directions = {
                "n": (0, -1, "north"), "north": (0, -1, "north"),
                "ne": (1, -1, "northeast"), "northeast": (1, -1, "northeast"),
                "e": (1, 0, "east"), "east": (1, 0, "east"),
                "se": (1, 1, "southeast"), "southeast": (1, 1, "southeast"),
                "s": (0, 1, "south"), "south": (0, 1, "south"),
                "sw": (-1, 1, "southwest"), "southwest": (-1, 1, "southwest"),
                "w": (-1, 0, "west"), "west": (-1, 0, "west"),
                "nw": (-1, -1, "northwest"), "northwest": (-1, -1, "northwest"),
            }
            if target in look_directions:
                dx, dy, direction = look_directions[target]
                nx, ny = (x + dx) % 100, (y + dy) % 100
                neighbor = ods.get_room(planet_id, nx, ny)
                detail = f"To the {direction}: [{nx}, {ny}] is {neighbor.biome['name']} biome."
                if neighbor.biome.get("hazard"):
                    detail += f" Warning: this is a hazardous area ({neighbor.biome['hazard']})."
                if neighbor.creatures:
                    detail += " Signs of wildlife: " + ", ".join(neighbor.creatures) + "."
                if neighbor.event:
                    detail += " " + neighbor.event
                if neighbor.items:
                    detail += " Visible discoveries: " + ", ".join(neighbor.items) + "."
                server_socket.sendto(detail.encode("utf-8"), address)
                return
            profile = get_profile(nickname)
            container = next((name for name in client_container_contents.get(address, {}) if target == name or target in name), None)
            if container:
                contents = client_container_contents[address][container]
                listing = ", ".join(f"{name} x{count}" if count > 1 else name for name, count in contents.items())
                server_socket.sendto((f"Inside {container}: " + (listing if listing else "nothing") + ".").encode("utf-8"), address)
                return
            if target == "sector center" and any(item == target and p == planet_id and bx == x and by == y for item, p, bx, by in profile["buildings"]):
                response = ("A large, gray brutalist building with few windows. It administers tourism and citizenship.\n"
                            "Rooms: central plaza, governor's office, factorium district.\n"
                            "Commands: relax, citizens, govern, sectormap, construction, buildings, resources, colony, events, roll-call, collection, modules, labor.")
                server_socket.sendto(response.encode("utf-8"), address)
            else:
                # Resolve exact names first, then allow a short look target such
                # as "asp" to identify a visible "wire asp". Search items and
                # creatures together so partial names behave consistently.
                item_name = next((name for name in room.items if name.lower() == target), None)
                creature_name = next((name for name in room.creatures if name.lower() == target), None)
                if item_name is not None:
                    server_socket.sendto(room.items[item_name].encode('utf-8'), address)
                elif creature_name is not None:
                    server_socket.sendto(f"A wild {creature_name}. It surveys the surroundings cautiously.".encode('utf-8'), address)
                else:
                    matches = [("item", name) for name in room.items if target in name.lower()]
                    matches += [("creature", name) for name in room.creatures if target in name.lower()]
                    if len(matches) == 1:
                        kind, name = matches[0]
                        if kind == "item":
                            response = room.items[name]
                        else:
                            response = f"A wild {name}. It surveys the surroundings cautiously."
                        server_socket.sendto(response.encode('utf-8'), address)
                    elif len(matches) > 1:
                        names = ", ".join(name for _, name in matches)
                        server_socket.sendto(f"Which do you mean: {names}?".encode('utf-8'), address)
                    else:
                        server_socket.sendto(f"You don't see a '{target}' here.".encode('utf-8'), address)
        else:
            send_look(address, server_socket)
        return

    if cmd in ("examine", "exam", "x"):
        target = " ".join(args).lower().strip()
        if target.startswith("at "):
            target = target[3:]
        candidates = list(client_inventories.get(address, {})) + list(room.items) + list(room.creatures)
        found, error = resolve_name(target, dict.fromkeys(candidates))
        if error:
            response = error
        elif not found:
            response = f"You don't see or carry '{target}'."
        elif found in room.creatures:
            response = f"A wild {found}. Commands: look {found}, pet {found}, feed {found}, attack {found}."
        else:
            description = client_inventories.get(address, {}).get(found, room.items.get(found, f"A {found}."))
            if found in client_container_contents.get(address, {}) or found in ("resource locker", "shipping container", "fiber backpack", "metal locker", "closet"):
                commands = f"Commands: look {found}, count <item> in {found}, put <item> in {found}, get <item> from {found}."
                client_container_contents[address].setdefault(found, {})
            else:
                commands = f"Commands: look {found}, drop {found}, count {found}."
                if found in RECIPES:
                    commands += f" Craft with: craft {found} on {RECIPES[found][0]}."
            response = f"{description}\n{commands}"
        server_socket.sendto(response.encode("utf-8"), address)
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
            elif cmd == "attack":
                matching_droid = next((droid for droid in room.hostile_droids if target in droid["name"].lower()), None)
                if not matching_droid:
                    server_socket.sendto(f"You do not see a '{target}' here to attack.".encode('utf-8'), address)
                elif not matching_droid["active"]:
                    server_socket.sendto(f"The {matching_droid['name']} is dormant.".encode('utf-8'), address)
                else:
                    damage = random.randint(20, 45)
                    matching_droid["health"] -= damage
                    result = f"You deal {damage} damage to the {matching_droid['name']}."
                    if matching_droid["health"] <= 0:
                        room.hostile_droids.remove(matching_droid)
                        room.items[f"{matching_droid['name']} remains"] = f"The wreckage of a {matching_droid['name']}."
                        room.items["spent cell casing"] = "A spent cell casing lies among the droid wreckage."
                        result += " The droid is destroyed; its remains can be looted."
                        if random.random() < 0.35:
                            tech = random.choice(("prototype targeting matrix", "advanced power cell", "droid logic core", "nanofiber spool", "major random stat relic"))
                            room.items[tech] = f"Advanced technology recovered from the {matching_droid['name']}: {tech}."
                            result += f" You recover {tech}."
                    else:
                        result += f" It has {matching_droid['health']} hit points remaining."
                    attackers = [droid for droid in room.hostile_droids if droid["active"]]
                    if attackers:
                        incoming = sum(random.randint(3, 9) for _ in attackers)
                        profile = get_profile(nickname)
                        profile["health"] = max(0, profile["health"] - incoming)
                        result += f" The hostile robots return fire for {incoming} damage (health {profile['health']}/100)."
                        if profile["health"] == 0:
                            profile["health"] = 50
                            result += " You are incapacitated and recover with 50 health."
                    server_socket.sendto(result.encode("utf-8"), address)
                    broadcast_to_room(f"--- {nickname} attacks a droid in the factory. ---",
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

    if cmd == "scavenge":
        profile = get_profile(nickname)
        poi_key = (planet_id, x, y)
        if room.poi_kind != "droid factory":
            response = "There is no point of interest here to scavenge. Look for [] markers on the map."
        elif room.hostile_droids:
            response = "The factory's hostile droids must be defeated before you can scavenge safely."
        elif poi_key in profile["scavenged_pois"]:
            response = "You have already scavenged this point of interest."
        else:
            profile["scavenged_pois"].add(poi_key)
            tech = next((name for name in room.items if name in ("prototype targeting matrix", "advanced power cell", "droid logic core", "nanofiber spool", "major random stat relic")), None)
            if tech:
                description = room.items.pop(tech)
                client_inventories[address][tech] = description
                client_stacks[address][tech] = client_stacks[address].get(tech, 0) + 1
                loot_msg = f"You recover {tech}."
            elif random.random() < 0.35:
                tech = random.choice(("prototype targeting matrix", "advanced power cell", "droid logic core", "nanofiber spool", "major random stat relic"))
                client_inventories[address][tech] = f"Recovered advanced technology: {tech}."
                client_stacks[address][tech] = client_stacks[address].get(tech, 0) + 1
                loot_msg = f"You recover {tech}."
            else:
                loot_msg = "You find only wreckage and spent casings."
            progress_msg = update_background_progress(nickname, "poi_scavenge")
            award_skillpoints(nickname, 10)
            response = f"You search the droid factory. {loot_msg}{progress_msg}"
        server_socket.sendto(response.encode("utf-8"), address)
        return

    # 8. Help
    if cmd == 'help':
        help_msg = (
            f"{BOLD}Wayfar 1444 Command Index:{RESET}\n"
            f"  {FG_CYAN}Movement:{RESET} n, ne, e, se, s, sw, w, nw (8 cardinal directions)\n"
            f"  {FG_CYAN}Tactical Map:{RESET} l or look; look <direction> scouts adjacent biome; map big|small, bigmap toggle, ansi on|off, blind on|off\n"
            f"  {FG_CYAN}Spawn Status:{RESET} $ods (displays active on demand rooms and cache)\n"
            f"  {FG_CYAN}Interplanetary:{RESET} planets, shuttle <planet_name>\n"
            f"  {FG_CYAN}Starships:{RESET} ships, craft or ship build <blueprint>, board <name>, ship fit <module>, launch, fly <direction>, land, ship harvest gas\n"
            f"  {FG_CYAN}Interaction:{RESET} look at <target>, take <item>, drop <item>, i (inventory)\n"
            f"  {FG_CYAN}Creatures:{RESET} pet <critter>, feed <critter>, attack <critter>\n"
            f"  {FG_CYAN}Backgrounds:{RESET} background list, background select <name>, background status (includes Scavenger)\n"
            f"  {FG_CYAN}Skills:{RESET} score, skills [group or name], learn <skill name>\n"
            f"  {FG_CYAN}Improvisation:{RESET} improvise, improvise on <tool>, improvise <product> on <tool> (requires Improvisation skill)\n"
            f"  {FG_CYAN}Crafting:{RESET} craft <product>, build <building>, datapad <query>, gather [material]\n"
            f"  {FG_CYAN}Tools:{RESET} harvest water and survey (atmo-thrasher condenser; 5s harvest, 10s survey)\n"
            f"  {FG_CYAN}Colony:{RESET} buildings, sectormap, resources, colony\n"
            f"  {FG_CYAN}Exploration:{RESET} [] marks a droid factory point of interest; defeat its robots, then scavenge\n"
            f"  {FG_CYAN}Social:{RESET} say <text>, emote <action>, sit <item>, exit"
        )
        server_socket.sendto(help_msg.encode('utf-8'), address)
        return

    if cmd in ('exit', 'quit'):
        handle_disconnect(address, server_socket)
        return

    # Fallback
    server_socket.sendto(f"Unknown command: '{cmd}'. Type 'help' for instructions.".encode('utf-8'), address)


def complete_timed_tool_actions(server_socket: socket.socket, now: float):
    """Finish condenser work without blocking the UDP server loop."""
    for address, action in list(timed_tool_actions.items()):
        if now < action["completes_at"]:
            continue
        timed_tool_actions.pop(address, None)
        if address not in clients:
            continue
        if client_locations.get(address) != action["location"]:
            message = "The condenser survey is interrupted because you left the area." if action["kind"] == "survey" else "The condenser harvest is interrupted because you left the area."
        elif action["kind"] == "harvest":
            inventory = client_inventories.get(address, {})
            stacks = client_stacks.get(address, {})
            inventory["water"] = "Unpurified water condensed from atmospheric moisture. Physical impurities were removed, but biological hazards may remain."
            stacks["water"] = stacks.get("water", 0) + 1
            message = "The condenser forms one bladder of unpurified water. Physical impurities were removed, but biological hazards may remain."
        else:
            planet_id, x, y = action["location"]
            room = ods.get_room(planet_id, x, y)
            resources = ", ".join(RESOURCE_BY_BIOME.get(room.biome_key, ())) or "none recorded"
            wildlife = ", ".join(room.creatures) or "no wildlife spotted"
            message = f"Survey complete: {room.biome['name']} biome at [{x}, {y}] on {planet_id}. Resources: {resources}. Wildlife: {wildlife}."
            if room.biome.get("hazard"):
                message += f" Hazard detected: {room.biome['hazard']}."
            if room.event:
                message += " " + room.event
        try:
            server_socket.sendto(message.encode("utf-8"), address)
        except OSError:
            pass


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

            complete_timed_tool_actions(server_socket, time.time())

            # Periodic cleanup of unused spawned rooms ($ODS)
            now = time.time()
            if now - last_cleanup_time > 60:
                active_locations = list(client_locations.values())
                ods.cleanup_empty_rooms(active_locations)
                last_cleanup_time = now

            time.sleep(0.02)


if __name__ == '__main__':
    main()
