// Pro Micro (ATmega32U4, 5 V) as a PS/2 keyboard.
// PS/2 CLOCK -> pin 2, DATA -> pin 3, GND -> GND. Host +5 V not connected.
// Bytes from USB serial are written to the PS/2 line verbatim: ps2term sends
// ready-made set-2 scancodes. No Serial1: an unconnected RX (D0, next to the
// PS/2 pins) picks up the clock as 0x00 bytes, which reach the host as
// keyboard overrun errors.
// Host->device commands are answered here and echoed to USB as "H xx" so the
// host side of the wire can be observed from the USB side.
#include <ps2dev.h>

PS2dev kbd(2, 3); // (clock, data)

static void report(const char *tag, uint8_t b) {
  if (!Serial)
    return;
  Serial.print(tag);
  if (b < 0x10)
    Serial.print('0');
  Serial.println(b, HEX);
}

// Answer one host command. ps2dev's own keyboard_reply() ignores commands it
// does not know, which makes BIOSes time out; ack everything unknown instead.
static void host_command() {
  uint8_t cmd, arg;
  if (kbd.read(&cmd))
    return; // framing/parity error: host will resend
  report("H ", cmd);
  switch (cmd) {
  case 0xFF: // reset -> ack, then self-test passed
    kbd.write(0xFA);
    delay(10);
    kbd.write(0xAA);
    break;
  case 0xF2: // identify -> MF2 keyboard
    kbd.write(0xFA);
    kbd.write(0xAB);
    kbd.write(0x83);
    break;
  case 0xEE: // echo
    kbd.write(0xEE);
    break;
  case 0xED: // LEDs <arg>
  case 0xF3: // typematic <arg>
  case 0xF0: // scancode set <arg>; arg 0 = query
    kbd.write(0xFA);
    if (kbd.read(&arg) == 0) {
      report("A ", arg);
      kbd.write(0xFA);
      if (cmd == 0xF0 && arg == 0)
        kbd.write(0x02);
    }
    break;
  case 0xFE: // resend: nothing buffered worth resending
  default:
    kbd.write(0xFA);
    break;
  }
}

// Send one byte, yielding to the host while it inhibits or talks to us.
static void send(uint8_t b) {
  unsigned long t0 = millis();
  while (millis() - t0 < 1000) {
    if (kbd.available()) {
      host_command();
      continue;
    }
    if (kbd.write(b) == 0)
      return;
    delayMicroseconds(200);
  }
  report("! drop ", b);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  kbd.write(0xAA); // power-on self-test passed; ignored if host is not up
}

void loop() {
  if (kbd.available())
    host_command();
  if (Serial.available())
    send(Serial.read());
}
