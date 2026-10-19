"""Lint mutations for the bench sketch. Every one is a real bench mistake.

python3 lint_cases.py <Fritzing binary> <dir with gen.py output>
"""

import sys

from gen import PIGTAIL

from mcubench.fritzing.linttest import move_wire_end, run, shift_instance
from mcubench.fritzing.part import MM, P


def socket_offset(src, dst):
    """Scene offset from socket pigtail pin src to dst."""
    return ((PIGTAIL.index(dst) - PIGTAIL.index(src)) * 5 * MM, 0)


CASES = [
    (
        "bench",
        "mirrored pinout: CLOCK on socket pin 6 instead of 5",
        lambda fz: move_wire_end(fz, "Pro Micro 2 to PS/2 5 CLOCK", *socket_offset(5, 6)),
    ),
    (
        "bench",
        "mirrored pinout: DATA on socket pin 2 instead of 1",
        lambda fz: move_wire_end(fz, "Pro Micro 3 to PS/2 1 DATA", *socket_offset(1, 2)),
    ),
    (
        "bench",
        "GND lead on the +5 V pin 4 instead of 3",
        lambda fz: move_wire_end(fz, "GND to PS/2 3", *socket_offset(3, 4)),
    ),
    ("bench", "Pro Micro one column right", lambda fz: shift_instance(fz, "Pro Micro", P, 0)),
]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(run(*sys.argv[1:], CASES))
