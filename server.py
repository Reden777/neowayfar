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
    client_inventories[address] = {}

    welcome = (
        f"{BOLD}{FG_CYAN}=== Welcome to Wayfar 1444 ==={RESET}\n"
        f"You awaken on {BOLD}{DEFAULT_PLANET}{RESET}.\n"
        f"Type {BOLD}help{RESET} for commands, {BOLD}$ods{RESET} for spawn status, or {BOLD}l{RESET} to look.\n"
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
            if target in room.items:
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
            items_str = ", ".join(inv.keys())
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
                    server_socket.sendto(f"You strike at the {matching_critter}! It scuttles back defensively.".encode('utf-8'), address)
                    broadcast_to_room(f"--- {nickname} lunges aggressively at the {matching_critter}! ---",
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
