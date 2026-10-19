SparkFun Pro Micro 5V/16MHz (DEV-12640, ATmega32U4) — schematic and pinout.
Pro_Micro_v13b.pdf                      https://cdn.sparkfun.com/datasheets/Dev/Arduino/Boards/Pro_Micro_v13b.pdf
ProMicro16MHzv2-graphical-datasheet.pdf https://cdn.sparkfun.com/assets/f/d/8/0/d/ProMicro16MHzv2.pdf
Hookup guide: https://learn.sparkfun.com/tutorials/pro-micro--fio-v3-hookup-guide
MCU datasheet (not vendored, 5 MB): https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7766-8-bit-AVR-ATmega16U4-32U4_Datasheet.pdf

Used pins: D2 -> PS/2 CLOCK, D3 -> PS/2 DATA, GND, USB (power + data), RST.
D0 (RX) stays unused and Serial1 is never started: it sits next to D2/D3 and
picks up the PS/2 clock when floating.
Bootloader is Caterina: 1200 bps touch on the CDC port or two RST->GND pulses
opens an 8 s avr109 window; ids 2341:0036 / 1b4f:9205.
