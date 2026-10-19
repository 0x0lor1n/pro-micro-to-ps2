// Stand-in for Harvie/ps2dev, included by firmware.ino under test/sim.cpp.
// The PS/2 wire is two queues: bytes the host sends (read side) and bytes the
// device wrote (write side). write() fails while the host inhibits the line.
#pragma once
#include <cstdint>
#include <deque>
#include <vector>

unsigned long millis();
void delayMicroseconds(unsigned int us);

struct PS2dev {
  std::deque<uint8_t> host;  // host -> device, consumed by read()
  std::vector<uint8_t> sent; // device -> host
  unsigned long inhibit_until = 0;
  bool bad_frame = false; // next read() reports a framing/parity error

  PS2dev(int, int) {}
  int available() { return !host.empty(); }
  int read(uint8_t *b) {
    if (host.empty())
      return -1;
    *b = host.front();
    host.pop_front();
    if (bad_frame) {
      bad_frame = false;
      return -2;
    }
    return 0;
  }
  int write(uint8_t b) {
    if (millis() < inhibit_until)
      return -1;
    sent.push_back(b);
    return 0;
  }
};
