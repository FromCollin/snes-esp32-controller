/*
 * snes_controller.ino
 * ───────────────────
 * SNES Controller Emulator for ESP32
 *
 * Receives 2 bytes over USB serial (little-endian button bitmask).
 * Responds to SNES CLK and LATCH signals via hardware interrupts.
 * Drives the DATA line with the correct active-low bit sequence.
 *
 * Bit mapping (PC convention, 1 = pressed):
 *   Bit 0  = B       Bit 4  = Up      Bit 8  = A
 *   Bit 1  = Y       Bit 5  = Down    Bit 9  = X
 *   Bit 2  = Select  Bit 6  = Left    Bit 10 = L
 *   Bit 3  = Start   Bit 7  = Right   Bit 11 = R
 *
 * Wiring:
 *   GPIO18 = CLK   (from SNES pin 2 via 74LVC245 level shifter)
 *   GPIO19 = LATCH (from SNES pin 3 via 74LVC245 level shifter)
 *   GPIO23 = DATA  (to SNES pin 4, direct — no level shifter needed)
 */

#define PIN_CLK    18
#define PIN_LATCH  19
#define PIN_DATA   23

volatile uint16_t buttonState = 0x0000;   // set by serial loop
volatile uint16_t shiftReg    = 0xFFFF;   // active-low shift register
volatile uint8_t  bitCount    = 0;        // bits clocked out so far

/*
 * onLatch — fires on FALLING edge of LATCH
 *
 * The SNES sends a 12us positive LATCH pulse then pulls it LOW.
 * On the falling edge we snapshot buttonState into shiftReg,
 * invert to active-low, and immediately drive the first bit (B)
 * onto DATA. The SNES samples DATA 6us later on the first CLK edge.
 *
 * Bits 12–15 are set HIGH (0xF000) — the SNES spec defines clock
 * cycles 13–16 as always HIGH, so we comply.
 */
void IRAM_ATTR onLatch() {
    shiftReg = (~buttonState & 0x0FFF) | 0xF000;
    bitCount = 0;
    digitalWrite(PIN_DATA, (shiftReg & 0x0001) ? HIGH : LOW);
    shiftReg >>= 1;
    bitCount = 1;
}

/*
 * onClock — fires on RISING edge of CLK
 *
 * Drive the next bit. The SNES samples DATA on the falling edge
 * ~6us after we drive it on the rising edge.
 * After all 16 bits, hold DATA LOW until the next LATCH.
 */
void IRAM_ATTR onClock() {
    if (bitCount >= 16) {
        digitalWrite(PIN_DATA, LOW);
        return;
    }
    digitalWrite(PIN_DATA, (shiftReg & 0x0001) ? HIGH : LOW);
    shiftReg >>= 1;
    bitCount++;
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_LATCH, INPUT);
    pinMode(PIN_CLK,   INPUT);
    pinMode(PIN_DATA,  OUTPUT);
    digitalWrite(PIN_DATA, LOW);   // idle low between polls
    attachInterrupt(digitalPinToInterrupt(PIN_LATCH), onLatch, FALLING);
    attachInterrupt(digitalPinToInterrupt(PIN_CLK),   onClock, RISING);
    Serial.println("SNES Controller Emulator Ready");
}

/*
 * loop — read 2-byte packets from PC over serial.
 * Little-endian: first byte = bits 0–7, second byte = bits 8–11.
 * buttonState is read by ISRs so updates take effect next LATCH.
 */
void loop() {
    if (Serial.available() >= 2) {
        uint8_t lo = Serial.read();
        uint8_t hi = Serial.read();
        buttonState = (uint16_t)lo | ((uint16_t)hi << 8);
    }
}
