# DCMotorTool

PySide6-based desktop application for DC motor measurement, visualization and future system identification.

The application is designed as a cross-platform measurement tool for:

- Windows
- Linux
- macOS

The primary target hardware is an STM32-based motor controller connected via USB.

The current version (V2) provides a complete software architecture for live data acquisition using a simulated measurement source. The architecture is prepared for later replacement of the simulator with real STM32 USB communication.

---

# Current Status

## Version: V2 - Acquisition Architecture

Implemented:

- PySide6 graphical user interface
- PyQtGraph high-performance plotting
- Live measurement tab
- Separate acquisition thread
- Acquisition controller layer
- Ring-buffer based data storage
- Simulated motor voltage/current data source
- Dynamic live scrolling plots
- Configurable display history length
- Motor voltage command interface placeholder

Not yet implemented:

- STM32 USB CDC communication
- Real ADC data acquisition
- Step-response measurement workflow
- Motor parameter identification
- Data logging
- Experiment management

---

# Software Architecture

The application follows a layered architecture.

The main design goal is:

> The GUI should only display data. Acquisition and hardware communication are separated from the user interface.

Current architecture:
                Main Window
                     |
                     |
             +-------+-------+
             |               |
          Live Tab       Analysis Tab
             |
             |
    Acquisition Controller
             |
             |
    Acquisition Worker
             |
      +------+------+
      |             |
Simulation       STM32 USB
(current)       (future)
