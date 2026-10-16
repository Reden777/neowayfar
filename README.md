# Wayfar 1444 UDP Engine

A Python recreation of the classic **Wayfar 1444** (Hellcore / LambdaMOO) sci-fi roguelike MUSH.

## Features
- **2D Perlin Noise & FBM**: Direct Python port of the C extension from `perlin2_hellcore.txt` using Ken Perlin's Improved Noise and permutation hashing.
- **On-Demand Spawn System (`$ODS`)**: Rooms are generated procedurally on demand as players move through planetary grids and are cached with Hellcore object IDs (e.g. `[#121157]`).
- **Tactical Viewport Map**: Side-by-side terminal rendering:
  - Left column: 17x13 ANSI tile map (2 characters wide per tile: `..`, `00`, `  `, `--`) with the player marked as `()`.
  - Right column: Room title, colored biome badge (e.g. `desert biome`, `forest biome`), and procedural descriptive sentences.
- **Three Planets (100×100 Grids)**:
  - `WY-1444`: Homeworld with forests, water, rocky peaks, and scrap plains.
  - `MO-52`: Desert world with sand dunes, canyons, and exposed metallic needles.
  - `AE-1655`: Alien anomaly wetland with murky pools and crystalline circles.
- **8-Directional Movement**: `n`, `ne`, `e`, `se`, `s`, `sw`, `w`, `nw`.
- **Ecology & Interactions**: Wild alien fauna (`muta-chicken`, `wire asp`, `silica scorpion`) that players can observe, pet, feed, or combat.

## How to Run

1. **Start the server**:
   ```bash
   python server.py
