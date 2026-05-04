"""
snes_keyboard.py
────────────────
Play SNES from your PC keyboard with true press/release tracking.
Uses pynput in a background thread so held keys stay active for
exactly as long as you physically hold them — no OS repeat rate involved.

Usage:
    python snes_keyboard.py --port /dev/ttyUSB0
    python snes_keyboard.py              # auto-detect port
"""

import time, struct, argparse, threading, serial, serial.tools.list_ports

try:
    from pynput import keyboard as kb
except ImportError:
    raise SystemExit("pip install pynput")

BTN_B      = 1 << 0
BTN_Y      = 1 << 1
BTN_SELECT = 1 << 2
BTN_START  = 1 << 3
BTN_UP     = 1 << 4
BTN_DOWN   = 1 << 5
BTN_LEFT   = 1 << 6
BTN_RIGHT  = 1 << 7
BTN_A      = 1 << 8
BTN_X      = 1 << 9
BTN_L      = 1 << 10
BTN_R      = 1 << 11


def find_port():
    for p in serial.tools.list_ports.comports():
        if any(x in p.device for x in ['USB', 'ACM', 'tty.SLAB', 'tty.usbserial']):
            return p.device
    return None


def main():
    parser = argparse.ArgumentParser(description="SNES keyboard controller")
    parser.add_argument('--port', default=None, help='Serial port e.g. /dev/ttyUSB0')
    args = parser.parse_args()

    port = args.port or find_port()
    if not port:
        raise SystemExit("No serial port found. Pass --port explicitly.")

    ser = serial.Serial(port, 115200, timeout=0)
    print(f"Connected on {port}")
    print()
    print("  Arrow keys  — d-pad")
    print("  Z           — jump (B)")
    print("  X           — run (Y)")
    print("  A           — spin jump (A)")
    print("  S           — X button")
    print("  Enter       — Start")
    print("  Backspace   — Select")
    print("  ESC or Q    — quit")
    print()

    held    = set()
    lock    = threading.Lock()
    running = threading.Event()
    running.set()

    def on_press(key):
        with lock:
            held.add(key)

    def on_release(key):
        with lock:
            held.discard(key)
        try:
            if key == kb.Key.esc or key.char == 'q':
                running.clear()
                return False
        except:
            pass

    listener = kb.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    try:
        while running.is_set():
            with lock:
                current = set(held)

            chars = set()
            for k in current:
                try:
                    if k.char:
                        chars.add(k.char.lower())
                except:
                    pass

            buttons = 0
            if kb.Key.right     in current: buttons |= BTN_RIGHT
            if kb.Key.left      in current: buttons |= BTN_LEFT
            if kb.Key.up        in current: buttons |= BTN_UP
            if kb.Key.down      in current: buttons |= BTN_DOWN
            if 'z'              in chars:   buttons |= BTN_B
            if 'x'              in chars:   buttons |= BTN_Y
            if 'a'              in chars:   buttons |= BTN_A
            if 's'              in chars:   buttons |= BTN_X
            if kb.Key.enter     in current: buttons |= BTN_START
            if kb.Key.backspace in current: buttons |= BTN_SELECT

            ser.write(struct.pack('<H', buttons))

            # Show active buttons in terminal
            names = []
            if buttons & BTN_RIGHT:  names.append("RIGHT")
            if buttons & BTN_LEFT:   names.append("LEFT")
            if buttons & BTN_UP:     names.append("UP")
            if buttons & BTN_DOWN:   names.append("DOWN")
            if buttons & BTN_B:      names.append("B(jump)")
            if buttons & BTN_Y:      names.append("Y(run)")
            if buttons & BTN_A:      names.append("A(spin)")
            if buttons & BTN_X:      names.append("X")
            if buttons & BTN_START:  names.append("START")
            if buttons & BTN_SELECT: names.append("SELECT")
            label = ", ".join(names) if names else "none"
            print(f"\rButtons: {label:<50}", end="", flush=True)

            time.sleep(1 / 60)

    except KeyboardInterrupt:
        pass
    finally:
        ser.write(struct.pack('<H', 0))
        ser.close()
        listener.stop()
        print("\nDisconnected.")


if __name__ == '__main__':
    main()
