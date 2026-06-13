# Bill of Materials

## Final BOM

| # | Item | Source | Price |
|---|---|---|---|
| 1 | 64×64 RGB LED Matrix — P3, 192×192mm, HUB75E | Amazon | ~$37.00 |
| 2 | Adafruit RGB Matrix Bonnet for Raspberry Pi (#3211) | Adafruit | $14.95 |
| 3 | 5V 4A switching PSU (matrix rail only) | Amazon | ~$12–15 |

**Estimated total: $64–67**

*IDC ribbon cable and power cable included with panel.*

## Notes

### Panel (Amazon ~$37)
- Confirmed specs: P3 pitch, 64×64, 192×192mm, HUB75E (5-bit row addressing), 1/32 scan, 5V/4A
- Driver IC unknown (not documented by seengreat); behaves correctly with default settings
  - FM6126A requires `--led-panel-type=FM6126A` flag in rpi-rgb-led-matrix, but this panel
    didn't need it
- Adafruit #4732 ($64.95) is the validated alternative if the Amazon panel has issues

### Bonnet — Adafruit #3211 ($14.95)
- Uses 74AHCT245 for 3.3V → 5V level shifting (TTL-input, CMOS-output)
- Pi 3B GPIO is 3.3V; HUB75E driver ICs are CMOS with VIH = 0.7×VDD = 3.5V — direct wiring is unreliable
- **Requires closing the E-address solder jumper** on the PCB before first use (enables 5th row address bit for 64-row panels; without it only top 32 rows display correctly)
- No PoE header conflict on Pi 3B
- Compatible with Pi 3B confirmed

### Power Supply (5V 4A)
- Matrix draws up to 4A at full white (64×64 @ 5V = 20W)
- Typical mixed-content draw: 1–2A
- Completely separate from the Pi's micro-USB 5V rail — do not share
- Feeds through the Bonnet's barrel jack input directly to the panel

## Waveshare Display Conflict Assessment
Existing Waveshare 5" Capacitive Touch Display is the **DSI variant** — no GPIO conflict.
DSI ribbon uses the dedicated MIPI DSI connector; touch I2C (GPIO 2/3) does not conflict
with the Bonnet. Display can remain attached during normal operation.
