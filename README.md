# turing-smart-screen-python
A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C (UART) display, also known as :
- Turing USB35INCHIPS / USB35INCHIPSV2
- 3.5 Inch Mini Screen
- [3.5 Inch 320*480 Mini Capacitive Touch Screen IPS Module](https://www.aliexpress.com/item/1005002505149293.html)

Operating systems supported : macOS, Windows, Linux (incl. Raspberry Pi) and all OS that support Python3
  
<img src="res/smart-screen-3.webp" width="500"/>

This is a 3.5" USB-C display that shows as a serial port once connected.
It cannot be seen by the operating system as a monitor but picture can be displayed on it.

A Windows-only software is [available here](https://translate.google.com/translate?sl=auto&u=https://gitee.com/emperg/usblcd/raw/master/dev0/realse.ini) to manage this display.
This software allows creating themes to display your computer sensors on the display, but does not offer a simple way to display custom pictures.

This Python script has been created to do some simple operations on this display like :
- **Display custom picture**
- Clear the screen (blank)
- Turn the screen on/off
- Display soft reset
- Set brightness


