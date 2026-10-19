// firmware.ino against a fake Arduino core (virtual clock) and a fake PS2dev.
#include <cstdint>
#include <cstdio>
#include <deque>
#include <string>
#include <vector>

#include "ps2dev.h"

#define HEX 16

static unsigned long now_us;
unsigned long millis() { return now_us / 1000; }
void delay(unsigned long ms) { now_us += ms * 1000; }
void delayMicroseconds(unsigned int us) { now_us += us; }

struct FakeSerial {
  std::deque<uint8_t> in;
  std::string out;
  bool connected = true;
  static void begin(unsigned long) {}
  explicit operator bool() const { return connected; }
  int available() { return (int)in.size(); }
  int read() {
    uint8_t c = in.front();
    in.pop_front();
    return c;
  }
  void print(const char *s) { out += s; }
  void print(char c) { out += c; }
  void println(unsigned v, int base) {
    char b[8];
    snprintf(b, sizeof b, base == HEX ? "%X" : "%u", v);
    out += b;
    out += "\n";
  }
};
static FakeSerial Serial;

#include "../src/firmware/firmware.ino"

static int failures;
static void check(bool ok, const char *what) {
  printf("%s %s\n", ok ? "ok  " : "FAIL", what);
  failures += !ok;
}

static void reset() {
  now_us = 0;
  Serial = FakeSerial();
  kbd = PS2dev(2, 3);
  setup();
  kbd.sent.clear();
}

static void host(std::vector<uint8_t> bytes) {
  kbd.host.insert(kbd.host.end(), bytes.begin(), bytes.end());
  while (kbd.available())
    loop();
}

static void usb(std::vector<uint8_t> bytes) {
  Serial.in.insert(Serial.in.end(), bytes.begin(), bytes.end());
  while (Serial.available() || kbd.available())
    loop();
}

using B = std::vector<uint8_t>;

int main() {
  now_us = 0;
  setup();
  check(kbd.sent == B{0xAA}, "power-up: self-test passed (AA)");

  reset();
  host({0xFF});
  check(kbd.sent == B({0xFA, 0xAA}), "FF reset -> FA AA");
  check(Serial.out == "H FF\n", "FF reported as H FF");

  reset();
  host({0xF2});
  check(kbd.sent == B({0xFA, 0xAB, 0x83}), "F2 identify -> FA AB 83 (MF2)");

  reset();
  host({0xED, 0x02});
  check(kbd.sent == B({0xFA, 0xFA}), "ED <leds> -> FA, FA");
  check(Serial.out == "H ED\nA 02\n", "ED argument reported as A 02");

  reset();
  host({0xF0, 0x00});
  check(kbd.sent == B({0xFA, 0xFA, 0x02}), "F0 00 query -> FA FA 02 (set 2)");

  reset();
  host({0xF0, 0x02});
  check(kbd.sent == B({0xFA, 0xFA}), "F0 02 set -> FA FA, no set byte");

  reset();
  host({0xEE});
  check(kbd.sent == B{0xEE}, "EE echo -> EE");

  reset();
  host({0xF4, 0xF5, 0xFE});
  check(kbd.sent == B({0xFA, 0xFA, 0xFA}), "unknown/F4/F5/FE -> FA each");

  reset();
  kbd.bad_frame = true;
  host({0xFF});
  check(kbd.sent.empty() && Serial.out.empty(),
        "bad frame: no reply, no report");

  reset();
  usb({0x1C, 0xF0, 0x1C});
  check(kbd.sent == B({0x1C, 0xF0, 0x1C}), "USB bytes go out verbatim ('a')");

  // Host inhibits for 300 ms: the byte waits, then goes out.
  reset();
  kbd.inhibit_until = 300;
  usb({0x1C});
  check(kbd.sent == B{0x1C} && Serial.out.empty(),
        "inhibited 300 ms: byte delivered late");

  // Host inhibits past the 1 s budget: the byte is dropped and reported.
  reset();
  kbd.inhibit_until = 5000;
  usb({0x1C});
  check(kbd.sent.empty() && Serial.out == "! drop 1C\n",
        "inhibited > 1 s: ! drop 1C");

  // Host command pending while a byte waits: answer it first, then send.
  reset();
  kbd.host.push_back(0xFF);
  usb({0x1C});
  check(kbd.sent == B({0xFA, 0xAA, 0x1C}),
        "host command answered before the pending byte");

  // No USB host: nothing is printed, replies still go out.
  reset();
  Serial.connected = false;
  host({0xFF});
  check(kbd.sent == B({0xFA, 0xAA}) && Serial.out.empty(),
        "no USB: silent, still answers");

  printf("%s\n", failures ? "FAILED" : "all passed");
  return failures != 0;
}
