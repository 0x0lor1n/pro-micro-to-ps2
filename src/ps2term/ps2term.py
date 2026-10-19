#!/usr/bin/env python3
"""Type on this machine, the Pro Micro replays it as a PS/2 keyboard into the target PC.

usage: ps2term [/dev/ttyACM0]      quit: Ctrl-]
Lines from the board ("H xx" = host command, "A xx" = its argument) are
printed as they arrive. Stdlib only.
"""

import os
import select
import sys
import termios
import time
import tty

# PS/2 scan code set 2: plain keys -> make code
# fmt: off
KEYS = {
    **dict(zip("abcdefghijklmnopqrstuvwxyz",
               [0x1C, 0x32, 0x21, 0x23, 0x24, 0x2B, 0x34, 0x33, 0x43, 0x3B,
                0x42, 0x4B, 0x3A, 0x31, 0x44, 0x4D, 0x15, 0x2D, 0x1B, 0x2C,
                0x3C, 0x2A, 0x1D, 0x22, 0x35, 0x1A], strict=True)),
    **dict(zip("1234567890", [0x16, 0x1E, 0x26, 0x25, 0x2E, 0x36, 0x3D,
                              0x3E, 0x46, 0x45], strict=True)),
    "-": 0x4E, "=": 0x55, "[": 0x54, "]": 0x5B, "\\": 0x5D, ";": 0x4C,
    "'": 0x52, "`": 0x0E, ",": 0x41, ".": 0x49, "/": 0x4A, " ": 0x29,
    "\r": 0x5A, "\n": 0x5A, "\t": 0x0D, "\x7f": 0x66, "\x08": 0x66,
}
SHIFTED = dict(zip('!@#$%^&*()_+{}|:"~<>?', '1234567890-=[]\\;\'`,./', strict=True))
LSHIFT, ESC = 0x12, 0x76
FKEYS = [0x05, 0x06, 0x04, 0x0C, 0x03, 0x0B, 0x83, 0x0A, 0x01, 0x09, 0x78, 0x07]
# escape sequence -> (extended?, code)
SEQ = {
    "[A": (1, 0x75), "[B": (1, 0x72), "[C": (1, 0x74), "[D": (1, 0x6B),
    "[H": (1, 0x6C), "[F": (1, 0x69), "[1~": (1, 0x6C), "[4~": (1, 0x69),
    "[2~": (1, 0x70), "[3~": (1, 0x71), "[5~": (1, 0x7D), "[6~": (1, 0x7A),
    "OP": (0, FKEYS[0]), "OQ": (0, FKEYS[1]), "OR": (0, FKEYS[2]),
    "OS": (0, FKEYS[3]),
    **{f"[{n}~": (0, FKEYS[i]) for i, n in
       enumerate([11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 23, 24])},
}
# fmt: on


def tap(code, ext=False, shift=False):
    pre = b"\xe0" if ext else b""
    out = b""
    if shift:
        out += bytes([LSHIFT])
    out += pre + bytes([code]) + pre + bytes([0xF0, code])
    if shift:
        out += bytes([0xF0, LSHIFT])
    return out


def ctrl(letter):  # Ctrl+<letter>
    return b"\x14" + tap(KEYS[letter]) + b"\xf0\x14"


def translate(buf):
    """Consume one key from buf; return (scancodes, rest)."""
    c = buf[0]
    if c == "\x1b":
        for seq in sorted(SEQ, key=len, reverse=True):
            if buf[1:].startswith(seq):
                ext, code = SEQ[seq]
                return tap(code, bool(ext)), buf[1 + len(seq) :]
        return tap(ESC), buf[1:]
    if c in KEYS:
        return tap(KEYS[c]), buf[1:]
    if c.isalpha() and c.lower() in KEYS:
        return tap(KEYS[c.lower()], shift=True), buf[1:]
    if c in SHIFTED:
        return tap(KEYS[SHIFTED[c]], shift=True), buf[1:]
    if "\x01" <= c <= "\x1a":
        return ctrl(chr(ord(c) + 96)), buf[1:]
    return b"", buf[1:]


def main():
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    tty.setraw(fd)
    termios.tcsetattr(fd, termios.TCSANOW, termios.tcgetattr(fd))
    old = termios.tcgetattr(0)
    tty.setraw(0)
    print(f"ps2term on {dev}; Ctrl-] quits, Ctrl-B toggles Del spam\r")
    line = b""
    spam = False
    try:
        while True:
            r, _, _ = select.select([0, fd], [], [], 0.1 if spam else None)
            if spam:
                os.write(fd, tap(0x71, ext=True))
            if fd in r:
                for b in os.read(fd, 256):
                    if b in (10, 13):
                        if line:
                            sys.stdout.write(f"  <{line.decode(errors='replace')}>\r\n")
                            sys.stdout.flush()
                        line = b""
                    else:
                        line += bytes([b])
            if 0 in r:
                buf = os.read(0, 64).decode(errors="ignore")
                if buf == "\x1b":  # lone Esc vs start of a sequence
                    time.sleep(0.05)
                    if select.select([0], [], [], 0)[0]:
                        buf += os.read(0, 64).decode(errors="ignore")
                if "\x1d" in buf:
                    break
                if "\x02" in buf:  # Ctrl-B: hammer Del until toggled off
                    spam = not spam
                    sys.stdout.write(f"  [Del spam {'ON' if spam else 'off'}]\r\n")
                    sys.stdout.flush()
                    buf = buf.replace("\x02", "")
                while buf:
                    codes, buf = translate(buf)
                    if codes:
                        os.write(fd, codes)
    finally:
        termios.tcsetattr(0, termios.TCSADRAIN, old)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        os.close(fd)


if __name__ == "__main__":
    main()
