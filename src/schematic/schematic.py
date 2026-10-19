"""Schematic: Pro Micro -> PS/2 socket of the target PC.

Pin numbers follow docs/wiring.d2 and src/fritzing/gen.py; change them there
too.

Usage: schematic.py OUT.svg
"""

import sys

import schemdraw
import schemdraw.elements as elm

from mcubench.schematic import IC, promicro, setup

setup()
OUT = sys.argv[1]

with schemdraw.Drawing(file=OUT, show=False) as d:
    d.config(unit=2.5, fontsize=10)

    # Same slots on both boxes, so every lead is one straight horizontal line.
    pm = promicro(
        [
            ("D2", "right", "3/3"),
            ("D3", "right", "2/3"),
            ("GND", "right", "1/3"),
        ],
        label="Pro Micro\nATmega32U4",
        edgepadW=2.5,  # the title must clear the D2/D3 labels
    )
    d += pm.right().at((0, 0))

    ps2 = elm.Ic(
        pins=[
            elm.IcPin(name="CLOCK", pin="5", side="left", slot="3/3"),
            elm.IcPin(name="DATA", pin="1", side="left", slot="2/3"),
            elm.IcPin(name="GND", pin="3", side="left", slot="1/3"),
            elm.IcPin(name="+5V", pin="4", side="right", slot="2/3"),
        ],
        **{**IC, "edgepadW": 2.4},
    ).label("PS/2 socket\nmini-DIN-6", loc="center", fontsize=10)
    d += ps2.right().anchor("CLOCK").at((pm.D2[0] + 6.0, pm.D2[1]))

    d += elm.Line().at(pm.D2).to(ps2.CLOCK).label("CLOCK", loc="top", fontsize=9)
    d += elm.Line().at(pm.D3).to(ps2.DATA).label("DATA", loc="top", fontsize=9)
    d += elm.Line().at(pm.GND).to(ps2.GND)
    mid = ((pm.GND[0] + ps2.GND[0]) / 2, pm.GND[1])
    d += elm.Dot().at(mid)
    d += elm.Line().at(mid).down(0.8)
    d += elm.Ground()
    d += elm.NoConnect().at(ps2["+5V"])

    d += (
        elm.Label()
        .at((pm.GND[0] - 4.5, pm.GND[1] - 3.2))
        .label(
            "Pro Micro: USB to the ps2term host (power + scancodes). PS/2 socket: on the target PC.\n"
            "Socket pin numbers as seen on its face; pins 2 and 6 are not connected.\n"
            "Pin 4 (+5 V) stays open: the board runs from USB.\n"
            "Pull-ups on CLOCK/DATA are the PC's (open collector).",
            loc="right",
            halign="left",
            valign="top",
            fontsize=9,
        )
    )

print(OUT)
