# SNES ESP32 Controller Emulator

Emulate a Super Nintendo controller using an ESP32 and a cut SNES extension cable. A Python script on your PC sends button states over USB serial and the ESP32 responds to the console's CLK and LATCH signals in real time.

Originally built as the hardware controller layer for a [DreamerV3](https://github.com/danijar/dreamerv3) AI agent playing Super Mario World on real hardware — but works as a general purpose SNES controller emulator for any project.

---

## How It Works

The SNES polls its controllers at 60Hz using a three-wire serial protocol:

1. The console sends a **12μs LATCH pulse** — the controller snapshots all button states
2. The console sends **16 CLK pulses** — the controller clocks out one bit per pulse on DATA
3. Logic is **active-low**: `0V = pressed`, `3.3V = not pressed`

The ESP32 listens for LATCH and CLK via hardware interrupts and drives the DATA line accordingly. Your PC sends a 2-byte button bitmask over USB serial at up to 60Hz and the ESP32 holds that state until the next update.

```
PC (Python)  -->  USB Serial  -->  ESP32  -->  DATA line  -->  SNES
                                     ^
                              CLK & LATCH
                              (from SNES via
                               level shifter)
```

---

## Hardware

| Component | Details |
|-----------|---------|
| ESP32 dev board | Any standard ESP32, USB powered |
| SNES extension cable | Cut the female end off, expose wires |
| 74LVC245A level shifter | 8-bit bus transceiver, DIP-20 |

### Why the 74LVC245A?

The SNES outputs CLK and LATCH at **5V logic**. The ESP32 GPIO pins are only **3.3V tolerant** — feeding them 5V directly risks damage over time. The 74LVC245A solves this:

- Operates at 1.65–3.6V VCC (powered from ESP32 3.3V rail — fully in spec)
- **Inputs accept up to 5.5V** — safe to connect directly to SNES 5V signals
- Outputs at VCC level (3.3V) — safe for ESP32 GPIOs

The DATA line does **not** go through the level shifter. DATA travels from ESP32 to SNES (not the other way), and the ESP32's 3.3V output comfortably exceeds the SNES 2V logic threshold.

> **Why not 74AHCT125?** The AHCT125 requires 4.5–5.5V VCC. Powering it at 3.3V from the ESP32 is out of spec. The LVC245 is the correct part.

---

## Wiring

### SNES Extension Cable Wire Colors

> ⚠️ Wire colors vary by cable manufacturer. The standard Nintendo cable uses White/Yellow/Orange/Red/Brown. Many third-party extension cables differ. **Always verify with a multimeter before wiring.**

Our cable (your colors may differ):

| SNES Pin | Signal | Wire Color | Destination |
|----------|--------|------------|-------------|
| 1 | +5V | Green | **Leave unconnected** |
| 2 | CLK | Blue | 74LVC245 A1 (pin 2) |
| 3 | LATCH | Yellow | 74LVC245 A2 (pin 3) |
| 4 | DATA | Red | ESP32 GPIO 23 (direct) |
| 5 | N/C | — | Leave unconnected |
| 6 | N/C | — | Leave unconnected |
| 7 | GND | Brown | ESP32 GND |

> **Why leave 5V unconnected?** The ESP32 is powered by USB. Connecting SNES 5V to ESP32 VIN while USB is also connected puts two power supplies on the same rail, which risks current fighting and potential damage.

### 74LVC245A Connections (DIP-20)

```
         ┌──────────────┐
DIR  1  ─┤              ├─ 20  VCC  → ESP32 3.3V (tie pins 1 and 20 together)
 A1  2  ─┤              ├─ 19  /OE  → GND
 A2  3  ─┤              ├─ 18  B1   → ESP32 GPIO18
 A3  4  ─┤              ├─ 17  B2   → ESP32 GPIO19
 A4  5  ─┤              ├─ 16  B3   (unused)
 A5  6  ─┤              ├─ 15  B4   (unused)
 A6  7  ─┤              ├─ 14  B5   (unused)
 A7  8  ─┤              ├─ 13  B6   (unused)
 A8  9  ─┤              ├─ 12  B7   (unused)
GND 10  ─┤              ├─ 11  B8   (unused)
         └──────────────┘
```

| Chip Pin | Signal | Connected To | Reason |
|----------|--------|-------------|--------|
| 1 (DIR) | Direction | ESP32 3.3V | HIGH = A→B direction (SNES→ESP32) |
| 2 (A1) | CLK in | SNES CLK wire | Receives 5V CLK from console |
| 3 (A2) | LATCH in | SNES LATCH wire | Receives 5V LATCH from console |
| 10 (GND) | Ground | ESP32 GND | Chip ground |
| 17 (B2) | LATCH out | ESP32 GPIO19 | 3.3V LATCH signal to ESP32 |
| 18 (B1) | CLK out | ESP32 GPIO18 | 3.3V CLK signal to ESP32 |
| 19 (/OE) | Output enable | GND | Active low — tie to GND to always enable |
| 20 (VCC) | Power | ESP32 3.3V | Powers chip — tie to DIR (pin 1) |

> **Tip:** Tie pins 1 (DIR) and 20 (VCC) together on the breadboard and run a single wire to ESP32 3.3V.

> **Why DIR → 3.3V (HIGH)?** The LVC245 is bidirectional. DIR HIGH = signals flow A→B. Since SNES signals arrive on the A side and the ESP32 is on the B side, DIR must be HIGH.

> **Why /OE → GND?** /OE is active-low output enable. Tied to GND means the chip is always enabled. If left floating the outputs may randomly disable.

### Complete Wiring Summary

```
SNES cable → 74LVC245 → ESP32
──────────────────────────────────────────────
SNES CLK   (blue)   → A1 (pin 2) → B1 (pin 18) → GPIO18
SNES LATCH (yellow) → A2 (pin 3) → B2 (pin 17) → GPIO19

SNES cable → ESP32 direct
──────────────────────────────────────────────
SNES DATA  (red)    → GPIO23
SNES GND   (brown)  → ESP32 GND

74LVC245 power/control
──────────────────────────────────────────────
Pin 1  (DIR) ─┬─ ESP32 3.3V
Pin 20 (VCC) ─┘
Pin 10 (GND)  → ESP32 GND
Pin 19 (/OE)  → GND
```

### Wiring Diagram

<!-- TODO: Add breadboard wiring photo here -->
![Wiring Diagram](images/wiring_diagram.png)

<!-- TODO: Add completed breadboard photo here -->
![Breadboard Photo](images/breadboard_photo.jpg)

---

## Software

### Requirements

```bash
pip install pyserial pynput
```

### Files

| File | Purpose |
|------|---------|
| `snes_controller.ino` | ESP32 firmware — flash this first |
| `snes_bridge.py` | Python class for sending actions over serial |
| `snes_keyboard.py` | Keyboard controller — play SNES from your PC keyboard |
| `test_serial_connection.py` | Verify ESP32 serial comms before wiring anything |
| `test_jump.py` | Hardware verification — makes Mario jump repeatedly |

---

## Quickstart

### 1. Flash the firmware

Open `snes_controller.ino` in Arduino IDE and flash it to your ESP32.

### 2. Verify serial connection (no SNES needed)

```bash
python test_serial_connection.py --port /dev/ttyUSB0
```

All 5 tests should pass. This confirms the ESP32 is running and accepting button packets before you touch any hardware.

### 3. Wire everything up

Follow the wiring diagram above. Power off the SNES before connecting.

### 4. Verify hardware with jump test

Power off SNES → plug in ESP32 via USB → power on SNES → run:

```bash
python test_jump.py --port /dev/ttyUSB0
```

Mario should jump every 2 seconds. If he does, hardware is confirmed working.

### 5. Play with keyboard

```bash
python snes_keyboard.py --port /dev/ttyUSB0
```

| Key | SNES Button | Action |
|-----|-------------|--------|
| Arrow keys | D-pad | Move |
| Z | B | Jump |
| X | Y | Run (hold while moving) |
| A | A | Spin jump |
| S | X | — |
| Enter | Start | Pause |
| Backspace | Select | — |
| ESC or Q | — | Quit |

---

## SNES Controller Protocol

Source: Jim Christy oscilloscope measurements, 1996.

```
                    12us
                 -->|  |<--

                     ---                          ---
                    |   |                        |   |
  LATCH         ---     --------/ /----------        ---
  CLOCK         ------  -  -  -  -/ /--------------  -
                      || | | | | |                 | |
                       -  -  -  -                   -
                       1  2  3  4                   1

  DATA             ---    ---    ---/ /        ---
  (B & Select     |   |  |   |  |            |
  pressed)    ----     ----    ----    -------
```

**Button order (clock cycle → button):**

| Cycle | Button | Bit | Cycle | Button | Bit |
|-------|--------|-----|-------|--------|-----|
| 1 | B | 0 | 9 | A | 8 |
| 2 | Y | 1 | 10 | X | 9 |
| 3 | Select | 2 | 11 | L | 10 |
| 4 | Start | 3 | 12 | R | 11 |
| 5 | Up | 4 | 13–16 | unused | always HIGH |
| 6 | Down | 5 | | | |
| 7 | Left | 6 | | | |
| 8 | Right | 7 | | | |

---

## Button Bitmask Reference

Send 2 bytes little-endian over serial. `1 = pressed` on the PC side — the ESP32 inverts to active-low for the SNES.

```python
BTN_B      = 1 << 0   # 0x0001
BTN_Y      = 1 << 1   # 0x0002
BTN_SELECT = 1 << 2   # 0x0004
BTN_START  = 1 << 3   # 0x0008
BTN_UP     = 1 << 4   # 0x0010
BTN_DOWN   = 1 << 5   # 0x0020
BTN_LEFT   = 1 << 6   # 0x0040
BTN_RIGHT  = 1 << 7   # 0x0080
BTN_A      = 1 << 8   # 0x0100
BTN_X      = 1 << 9   # 0x0200
BTN_L      = 1 << 10  # 0x0400
BTN_R      = 1 << 11  # 0x0800
```

**Example — send RIGHT + JUMP (B):**
```python
import serial, struct
ser = serial.Serial('/dev/ttyUSB0', 115200)
ser.write(struct.pack('<H', 0x0081))  # RIGHT | B
```

---

## Using SNESBridge in Your Own Code

```python
from snes_bridge import SNESBridge

bridge = SNESBridge(port='/dev/ttyUSB0')

# Send a named action (DreamerV3 action space)
bridge.send_action(3)   # RIGHT+JUMP

# Send raw button bitmask
bridge.send_buttons(BTN_RIGHT | BTN_B)

# Release all buttons
bridge.release_all()

bridge.close()
```

### DreamerV3 Action Space

| Index | Name | Bitmask |
|-------|------|---------|
| 0 | NOOP | 0x0000 |
| 1 | RIGHT | 0x0080 |
| 2 | RIGHT+RUN | 0x0082 |
| 3 | RIGHT+JUMP | 0x0081 |
| 4 | RIGHT+RUN+JUMP | 0x0083 |
| 5 | LEFT | 0x0040 |
| 6 | LEFT+JUMP | 0x0041 |
| 7 | JUMP | 0x0001 |
| 8 | UP | 0x0010 |
| 9 | DOWN | 0x0020 |
| 10 | SPIN (A) | 0x0100 |
| 11 | SPIN+RIGHT | 0x0180 |
| 12 | SPIN+LEFT | 0x0140 |
| 13 | SPIN+RIGHT+RUN | 0x0182 |

---

## Troubleshooting

**Mario pauses as soon as ESP32 is connected**
The ESP32 GPIO floats before firmware initialises and the SNES reads phantom button presses. Always power off the SNES, plug in the ESP32, then power on the SNES.

**Buttons not registering at all**
Check that /OE (chip pin 19) is tied to GND. If floating, chip outputs are disabled and CLK/LATCH never reach the ESP32.

**Wrong buttons registering consistently**
CLK and LATCH are likely swapped. Verify blue wire goes to A1 (pin 2) → B1 (pin 18) → GPIO18, and yellow wire goes to A2 (pin 3) → B2 (pin 17) → GPIO19.

**Keyboard feels laggy or releases early**
Normal with curses-based input. Use `snes_keyboard.py` which uses pynput with true press/release tracking in a background thread.

**Serial port not found**
Check `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`. Pass the port explicitly with `--port /dev/ttyUSB0`.

---

## Notes on Hot-Plugging

The SNES was not designed for hot-plugging controllers. Plugging the ESP32 in while the console is running causes pin contact transients that the SNES reads as phantom button presses. The correct procedure is always:

1. Power off SNES
2. Connect ESP32 (USB already plugged in is fine)
3. Power on SNES

A 10kΩ pull-down resistor on GPIO23 (DATA) would hold the line LOW during ESP32 boot and reduce this, but is not strictly necessary if you follow the power-on order above.

---

## Why Software Interrupts (Not RMT/Hardware)?

A common question for ESP32 controller projects. The short answer: the SNES drives the timing, the ESP32 only reacts to it.

The N64 controller protocol requires the controller to **generate** precise 1μs/3μs pulses autonomously — software can't reliably hit that, so hardware timers (RMT) are necessary.

The SNES protocol has the console driving CLK and LATCH. The ESP32 just needs to put the right bit on DATA when CLK rises. The minimum timing window is 6μs — far wider than a software interrupt response time of ~100–300ns on the ESP32. `IRAM_ATTR` ISRs run from SRAM so there's no flash cache latency. Software interrupts are the right and sufficient approach here.

---

## License

MIT
