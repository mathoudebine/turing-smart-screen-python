# turing-smart-screen-python
A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C (UART) display, also known as :
- Turing USB35INCHIPS / USB35INCHIPSV2
- 3.5 Inch Mini Screen
- [3.5 Inch 320*480 Mini Capacitive Touch Screen IPS Module](https://www.aliexpress.com/item/1005002505149293.html)

Operating systems supported : macOS, Windows, Linux (incl. Raspberry Pi) and all OS that support Python3
  
<img src="res/smart-screen-3.webp" width="500"/>

This is a 3.5" USB-C display that shows as a serial port once connected.
It cannot be seen by the operating system as a monitor but picture can be displayed on it.

A Windows-only software is [available in Chinese](https://lgb123-1253504678.cos.ap-beijing.myqcloud.com/35inch.rar) or [in English](https://lgb123-1253504678.cos.ap-beijing.myqcloud.com/35inchENG.rar) to manage this display.
This software allows creating themes to display your computer sensors on the screen, but does not offer a simple way to display custom pictures or text.

This Python script has been created to do some simple operations on this display like :
- **Display custom picture**
- **Display text**
- **Display progress bar**
- Clear the screen (blank)
- Turn the screen on/off
- Display soft reset
- Set brightness
