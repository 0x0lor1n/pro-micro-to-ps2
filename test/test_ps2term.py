"""Scancode translation in ps2term (set 2), no serial port needed."""

import unittest

from ps2term import ctrl, tap, translate

BREAK = 0xF0


def run(buf):
    out = b""
    while buf:
        codes, buf = translate(buf)
        out += codes
    return out


class Translate(unittest.TestCase):
    def test_letter(self):
        self.assertEqual(run("a"), bytes([0x1C, BREAK, 0x1C]))

    def test_upper_is_shifted(self):
        self.assertEqual(run("A"), bytes([0x12, 0x1C, BREAK, 0x1C, BREAK, 0x12]))

    def test_shifted_symbol(self):
        self.assertEqual(run("!"), tap(0x16, shift=True))

    def test_enter(self):
        self.assertEqual(run("\r"), tap(0x5A))

    def test_arrow_is_extended(self):
        self.assertEqual(run("\x1b[A"), bytes([0xE0, 0x75, 0xE0, BREAK, 0x75]))

    def test_delete(self):
        self.assertEqual(run("\x1b[3~"), tap(0x71, ext=True))

    def test_f1_and_f12(self):
        self.assertEqual(run("\x1bOP"), tap(0x05))
        self.assertEqual(run("\x1b[24~"), tap(0x07))

    def test_lone_escape(self):
        self.assertEqual(run("\x1b"), tap(0x76))

    def test_ctrl_letter(self):
        self.assertEqual(run("\x03"), ctrl("c"))
        self.assertEqual(ctrl("c"), bytes([0x14, 0x21, BREAK, 0x21, BREAK, 0x14]))

    def test_unknown_dropped(self):
        self.assertEqual(run("é"), b"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
