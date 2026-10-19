"""Generate the bench sketch (Fritzing .fzz): Pro Micro to a PS/2 socket.

  python3 gen.py <fritzing-parts-dir> <out-dir>

Placement, net checks and the .fzz writer are in mcubench.fritzing (mcu-bench). Fritzing
ships no PS/2 socket, so it is generated here and embedded in the .fzz.
"""

import functools
import os
import sys

from mcubench.fritzing import part as fzpart
from mcubench.fritzing import promicro
from mcubench.fritzing.part import MM, text
from mcubench.fritzing.sketch import BLACK, BLUE, YELLOW, Sketch

PM_ID = "pro-micro-to-ps2-sfe-pro-micro-5v"
PS2_ID = "pro-micro-to-ps2-minidin6-socket"

GenPart = functools.partial(fzpart.GenPart, author="pro-micro-to-ps2/src/fritzing/gen.py", tag="pro-micro-to-ps2")

# Socket face (what you look at on the back of the PC), key up. Offsets from
# the centre in mm, scaled up from the real 1.3 mm pitch so labels fit.
PS2 = {
    1: ("DATA", 3.0, 6.0),
    2: ("NC", -3.0, 6.0),
    3: ("GND", 6.5, 1.0),
    4: ("+5V", -6.5, 1.0),
    5: ("CLOCK", 4.5, -4.5),
    6: ("NC", -4.5, -4.5),
}


# Pigtail order, left to right: matches the Pro Micro columns (GND 4, D2 6,
# D3 7) so the wires to the board do not cross.
PIGTAIL = [3, 5, 1, 4, 2, 6]


def ps2_socket():
    """Mini-DIN-6 socket, face view, with a pigtail header along the top edge.

    Connector i = pin i + 1. The pins sit on the pigtail; thin lines in the art
    tie each to its hole in the face, so the drawing shows where every lead
    really lands. Face view is the mirror of the plug's solder side; a pinout
    read off a plug diagram puts CLOCK and DATA on the NC pins 6 and 2.
    """
    w, h = 34 * MM, 43 * MM
    cx, cy = w / 2, 25.5 * MM
    hy = 4 * MM  # pigtail row
    hx = lambda n: w / 2 + (PIGTAIL.index(n) - 2.5) * 5 * MM
    p = GenPart(
        PS2_ID,
        "PS/2 socket",
        "J",
        "connector",
        "PS/2 keyboard socket (mini-DIN-6, female), face view: 1 DATA, 3 GND, 4 +5V, 5 CLOCK, 2/6 NC.",
        w,
        h,
        "female",
    )
    a = p.art
    a.append(f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" rx="4" fill="#3a3a3a"/>')
    a.append(
        f'<rect x="{hx(3) - 2.5 * MM:.2f}" y="{hy - 2 * MM:.2f}" width="{30 * MM:.2f}" height="{4 * MM:.2f}" fill="#111111"/>'
    )
    a.append(
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{11 * MM:.2f}" fill="#b17ad1" stroke="#c0c0c0" stroke-width="3"/>'
    )
    a.append(
        f'<rect x="{cx - 1.5 * MM:.2f}" y="{cy - 10.5 * MM:.2f}" width="{3 * MM:.2f}" height="{3 * MM:.2f}" fill="#3a3a3a"/>'
    )
    for n, (name, dx, dy) in PS2.items():
        x, y = cx + dx * MM, cy + dy * MM
        nc = name == "NC"
        color = "#bbbbbb" if nc else "#ffffff"
        a.append(
            f'<line x1="{hx(n):.2f}" y1="{hy + 8 * MM:.2f}" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="{color}" stroke-width="0.8" stroke-dasharray="{"2,2" if nc else "none"}"/>'
        )
        a.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{1.1 * MM:.2f}" fill="#222222" stroke="{color}" stroke-width="0.6"/>'
        )
        a.append(text(x, y + 0.8 * MM, str(n), 3.5, color, weight="bold"))
        a.append(text(hx(n), hy + 4.5 * MM, str(n), 4, color, weight="bold"))
        a.append(text(hx(n), hy + 6.8 * MM, name, 3.2, color))
        p.pin(f"{n} {name}", hx(n), hy, "L" if dx < 0 else "R")
    a.append(text(w / 2, h - 1.2 * MM, "PS/2 socket, face view", 4.5, "#ffffff"))
    return p


def ps2_pin(n):
    return f"connector{n - 1}"


def bench(parts):
    """No rails: the board runs from USB, GND comes from the Pro Micro's own
    GND pin, and the PC's +5 V (socket pin 4) stays unconnected."""
    sk = Sketch(parts)
    pm = promicro.place(sk, PM_ID, "Pro Micro", col0=2)

    ps2 = sk.embed(PS2_ID, "PS/2 socket", ps2_socket().files())
    ps2.place(ps2_pin(3), (14, 215))
    # Breadboard end first: lint mutations move the socket end (x2).
    # place() plugs only the top-row GND (promicro.conn picks the first match):
    # hop it to the free column 1 and across the gap, so all three leads drop
    # straight down in socket order (GND 1, D2 6, D3 7) without crossing.
    sk.wire("pin3J", "pin1J", BLACK, "GND to column 1")
    sk.wire("pin1F", "pin1E", BLACK, "GND across the gap")
    sk.wire("pin1A", (ps2, ps2_pin(3)), BLACK, "GND to PS/2 3")
    sk.wire("pin6A", (ps2, ps2_pin(5)), BLUE, "Pro Micro 2 to PS/2 5 CLOCK")
    sk.wire("pin7A", (ps2, ps2_pin(1)), YELLOW, "Pro Micro 3 to PS/2 1 DATA")

    for k, part in enumerate((pm, ps2)):
        part.sch = (k * 200, 0)
        part.pcb = (k * 120, 0)

    pmn = lambda pin: ("Pro Micro", promicro.conn(pin))
    sk.check(
        {
            "GND": [pmn("GND"), ("PS/2 socket", ps2_pin(3))],
            "CLOCK": [pmn("2"), ("PS/2 socket", ps2_pin(5))],
            "DATA": [pmn("3"), ("PS/2 socket", ps2_pin(1))],
        }
    )
    sk.note(
        420,
        0,
        380,
        200,
        "Прошивка: flash. Питание только по USB.\n"
        "PS/2 гнездо на ПК, вид с лица, ключ сверху:\n"
        "1 DATA, 3 GND, 5 CLOCK; 4 (+5 V) не подключать.\n"
        "Перед включением прозвонить при выключенном ПК:\n"
        "D2 → гнездо 5, D3 → гнездо 1, GND → гнездо 3,\n"
        "каждый провод звенит только на своём пине.\n"
        "Звенит на 6 или 2 — распиновка зеркальная.",
    )
    return sk


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    parts, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    bench(parts).save(os.path.join(out, "bench.fzz"), "bench")
    print(os.path.join(out, "bench.fzz"))


if __name__ == "__main__":
    main()
