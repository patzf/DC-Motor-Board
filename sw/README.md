# DCMotorTool

PySide6-based desktop application for DC motor measurement, visualization and future system identification.

## Current live acquisition

The live measurement path now reads real STM32 USB VCP/serial data.

Current STM32 stream assumptions:

- One channel: motor-current ADC value
- ADC resolution: 12 bit (`0 ... 4095`)
- One sample every 1 ms (1000 samples/s)
- Each sample is transmitted as a little-endian `uint16_t` (2 bytes)
- 100 samples / 200 bytes are expected every 100 ms
- No framing/header/timestamp exists yet
- The first byte received after acquisition starts is treated as the beginning of the stream
- Scaling from raw ADC value to amperes is intentionally not implemented yet

The acquisition worker accumulates serial bytes and converts every complete pair of bytes into one ADC sample. It does not assume that one serial read corresponds to one 200-byte block.

The existing motor-current live plot displays a configurable rolling history (1 s to 60 s). The existing motor-voltage plot and controls remain in the GUI, but no simulated live voltage/current data is generated.

## Serial configuration

The Live Measurement tab provides:

- Serial-port selection
- Port refresh
- Configurable baud rate (default 460800)

For USB CDC devices, the effective baud rate may be ignored by the USB device, but the serial-port driver still accepts a baud-rate setting.

## Offline / analysis functionality

The Motor Identification / Step Response tab has not been changed by the live UART implementation.

## Dependencies

Install the Python dependencies with:

```text
pip install -r requirements.txt
```

Run:

```text
python main.py
```
