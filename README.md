# Wayfar 1444 UDP Engine

A Python recreation of the classic **Wayfar 1444** (Hellcore / LambdaMOO) sci-fi roguelike MUSH.

## Features
- **2D Perlin Noise & FBM**: Direct Python port of the C extension from `perlin2_hellcore.txt` using Ken Perlin's Improved Noise and permutation hashing.
- **On-Demand Spawn System (`$ODS`)**: Rooms are generated procedurally on demand as players move through planetary grids and are cached with Hellcore object IDs (e.g. `[#121157]`).
- **Tactical Viewport Map**: Side-by-side terminal rendering:
  - Left column: 17x13 ANSI tile map (2 characters wide per tile: `..`, `00`, `  `, `--`) with the player marked as `()`.
  - Right column: Room title, colored biome badge (e.g. `desert biome`, `forest biome`), and procedural descriptive sentences.
- **Map Preferences**: `map big` or `bigmap on` selects a 21x21 viewport; `map small` returns to 17x13. `ansi off` or `blind on` omits ANSI control sequences from map and room output. Coordinate biome lookups are cached for quicker redraws.
- **Three Planets (100×100 Grids)**:
  - `WY-1444`: Homeworld with forests, water, rocky peaks, and scrap plains.
  - `MO-52`: Desert world with sand dunes, canyons, and exposed metallic needles.
  - `AE-1655`: Alien anomaly wetland with murky pools and crystalline circles.
- **8-Directional Movement**: `n`, `ne`, `e`, `se`, `s`, `sw`, `w`, `nw`.
- **Ecology & Interactions**: Wild alien fauna (`muta-chicken`, `wire asp`, `silica scorpion`) that players can observe, pet, feed, or combat.
- **Character Backgrounds**: Select Ranger, Fabricator, Retiree, Student, Lab Tech, Botanist, or Hacker with `background select <name>`. Use `background list` and `background status` to view objectives and progress. Ranger wildlife defeats, Fabricator crafting, and Retiree construction currently progress; completing them awards the listed reroll points. Hacker requires five reroll points to unlock. Botanist lists its starting skills. Profiles last for the current server process; research, discovery, hacking, and starship background objectives await those game systems.
- **Scavenger Background and POIs**: The Scavenger background tracks ten planetary POIs scavenged and awards one reroll point. Rare abandoned droid factories are marked `[]` on the map, contain sleeping hostile cell-bomber and assembler droids, and may yield advanced technology. The robots wake when a named player enters; defeat them before using `scavenge`.
- **Manual Crafting**: New characters carry a basic crafting tool and colonial assembly datapad. Use `datapad <query>` or `lookup <query>` for known recipes, `gather [material]` to collect local resources, and `craft <product>` to make an item with the required tool and ingredients. Crafting consumes ingredients and produces quality 75 items; Fabricator progress counts each qualifying product.
- **Equipment Crafting Tool**: Unlock it with a basic crafting tool, one weak power emitter, and two solid-phase metal. Once crafted, it unlocks the equipment product catalog across weapons, armor, tools, components, ammunition, containers, gadgets, modules, and products.
- **Engineering Tool**: Craft it with a basic crafting tool, one weak power emitter, and two inert metal fragments (complexity 10.0). It unlocks the experimental starship assembly tool and the listed automated machines, structures, and products. Their individual ingredient recipes are compact engine approximations because the reference does not provide them.
- **Structure, Defensive, Advanced Structure, and Component Tools**: These tool catalogs are available through the datapad and crafting system. The Structure Tool requires one weak power emitter, four solid-phase metal, and four inert casings (complexity 15.0). Use `build <building>` with a structure-related tool to deploy buildings; Retiree progress counts completed placements. Product recipes are compact engine approximations where the reference gives no ingredients.
- **Material Processor and Structures**: Craft the Material Processor with a Structure Tool, three weak power emitters, four solid-phase metal, and four inert casings (complexity 20.0). It can make the listed resources and components. Added documented requirements and complexities for the supplied structure components, weak power emitter, automated mining plant, factory, Sector Center, warehouses, laboratory, and refinery. Native lumber and solid-phase metal can be gathered in matching biomes. `buildings`, `sectormap`, `resources`, and `colony` provide basic colony readouts; Sector Centers are limited to five per character and place a resource locker.
- **Skills**: Browse skill groups with `skills`, inspect with `skills <group or skill>`, buy with `learn <skill name>`, and check points with `score`. Costs and prerequisites follow the supplied skill reference. Botanist grants Heavy Tan, Sightseer, and Developing Observation when selected. Combat, crafting, and construction award skillpoints; skill effects on action rolls are not modeled yet. The Improvisation skill enables `improvise on <tool>` and `improvise <product> on <tool>`.

## How to Run

1. **Start the server**:
   ```bash
   python server.py
