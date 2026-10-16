import socket
import threading
import sys
import os

# Server configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 60025

# Windows ANSI escape sequence support
if os.name == 'nt':
    try:
        import colorama
        colorama.init()
    except ImportError:
        os.system('')  # Enable VT100 interpretation in Windows Console


def receive_loop(sock: socket.socket):
    """Continuously receives and prints server packets."""
    while True:
        try:
            data, _ = sock.recvfrom(8192)
            if not data:
                break
            message = data.decode('utf-8', errors='ignore')
            # Print message cleanly above the user prompt
            print(f"\r{message}\n> ", end="", flush=True)
        except OSError:
            break
        except Exception as e:
            print(f"\n[Connection error: {e}]")
            break


def main():
    print("========================================")
    print("           WAYFAR 1444 CLIENT           ")
    print("========================================")

    nickname = input("Enter your persona callsign: ").strip()
    if not nickname:
        nickname = "Traveler"

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Start background receive thread
        receiver = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
        receiver.start()

        # Send initial join notification
        sock.sendto(f"--- {nickname} has joined the chat ---".encode('utf-8'), (SERVER_HOST, SERVER_PORT))

        known_commands = {
            'l', 'look', 'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw',
            'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest',
            '$ods', 'ods', 'planets', 'shuttle', 'planet', 'take', 'drop',
            'i', 'inv', 'inventory', 'pet', 'feed', 'attack', 'sit', 'background', 'backgrounds',
            'craft', 'build', 'construct', 'datapad', 'lookup', 'gather', 'score', 'skills', 'skill', 'learn', 'improvise',
            'buildings', 'sectormap', 'resources', 'colony',
            'emote', ':', 'say', "'", 'help'
        }

        while True:
            try:
                line = input("> ").strip()
                if not line:
                    continue

                if line.lower() in ('exit', 'quit', '/exit', '/quit'):
                    sock.sendto(f"exit {nickname}".encode('utf-8'), (SERVER_HOST, SERVER_PORT))
                    print("Disconnecting from Wayfar network.")
                    break

                parts = line.split(' ', 1)
                first_word = parts[0].lower()

                if first_word in known_commands:
                    args = parts[1] if len(parts) > 1 else ""
                    packet = f"{first_word} {args} {nickname}".strip()
                else:
                    # Regular chat
                    packet = f"{nickname}: {line}"

                sock.sendto(packet.encode('utf-8'), (SERVER_HOST, SERVER_PORT))

            except (KeyboardInterrupt, EOFError):
                sock.sendto(f"exit {nickname}".encode('utf-8'), (SERVER_HOST, SERVER_PORT))
                print("\nExiting.")
                break


if __name__ == '__main__':
    main()
