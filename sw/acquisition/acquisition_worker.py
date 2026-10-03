import serial
from serial.tools import list_ports

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    QTimer
)

from models.measurement_sample import MeasurementSample


class AcquisitionWorker(QObject):

    sampleReady = Signal(
        MeasurementSample
    )

    connectionChanged = Signal(
        bool
    )

    acquisitionChanged = Signal(
        bool
    )

    errorOccurred = Signal(
        str
    )

    portsChanged = Signal(
        list
    )


    def __init__(self):

        super().__init__()

        self.connected = False
        self.running = False

        self.sample_rate = 1000

        self.serial = None
        self.port = ""
        self.baudrate = 460800

        # Raw serial bytes are accumulated here.  There is deliberately
        # no packet/header parsing yet: every pair of bytes is one
        # little-endian uint16_t ADC sample.
        self.rx_buffer = bytearray()

        self.sample_index = 0
        self.poll_timer = None


    @Slot()
    def initialize(self):

        """
        Called after the worker is moved into its QThread.
        """

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(5)
        self.poll_timer.timeout.connect(self.read_serial)

        self.refresh_ports()


    @Slot()
    def refresh_ports(self):

        ports = [
            port.device
            for port in list_ports.comports()
        ]

        self.portsChanged.emit(ports)


    @Slot(str, int)
    def set_serial_config(self, port, baudrate):

        self.port = port.strip()
        self.baudrate = int(baudrate)


    @Slot()
    def connect_device(self):

        if self.connected:
            return

        if not self.port:
            self.errorOccurred.emit(
                "No serial port selected"
            )
            return

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0
            )

            # Start at a clean stream boundary.  No protocol/header exists
            # yet, so the first byte received after connection is byte 0
            # of the measurement stream.
            self.rx_buffer.clear()
            self.sample_index = 0

            self.connected = True

            self.connectionChanged.emit(True)

        except (serial.SerialException, OSError) as exc:

            self.serial = None
            self.connected = False

            self.errorOccurred.emit(
                f"Could not open {self.port}: {exc}"
            )


    @Slot()
    def disconnect_device(self):

        self.stop()

        if self.serial is not None:

            try:
                self.serial.close()

            except (serial.SerialException, OSError):
                pass

            self.serial = None

        self.connected = False
        self.rx_buffer.clear()

        self.connectionChanged.emit(False)


    @Slot()
    def start(self):

        if not self.connected or self.serial is None:

            self.errorOccurred.emit(
                "Device not connected"
            )

            return

        self.running = True

        self.sample_index = 0
        self.rx_buffer.clear()

        self.poll_timer.start()

        self.acquisitionChanged.emit(True)


    @Slot()
    def stop(self):

        if self.poll_timer:
            self.poll_timer.stop()

        self.running = False

        self.acquisitionChanged.emit(False)


    @Slot(float)
    def set_motor_voltage(self, voltage):

        """
        Reserved for a future STM32 command protocol.
        """

        print(
            f"Motor voltage command: {voltage:.2f} V"
        )


    def read_serial(self):

        """
        Read all currently available VCP bytes without blocking the GUI.

        The STM32 currently sends one little-endian uint16_t ADC value
        per sample.  At 1 kHz this corresponds to 100 samples / 200 bytes
        per 100 ms.  Since there is no framing protocol yet, every pair
        of bytes is interpreted as one sample.
        """

        if not self.running or self.serial is None:
            return

        try:

            available = self.serial.in_waiting

            if available <= 0:
                return

            self.rx_buffer.extend(
                self.serial.read(available)
            )

        except (serial.SerialException, OSError) as exc:

            self.errorOccurred.emit(
                f"Serial read error: {exc}"
            )

            self.stop()
            return

        complete_bytes = (
            len(self.rx_buffer) // 2
        ) * 2

        if complete_bytes == 0:
            return

        data = self.rx_buffer[:complete_bytes]

        del self.rx_buffer[:complete_bytes]

        for index in range(
            0,
            len(data),
            2
        ):

            # STM32 / ARM is little-endian.  Make this explicit so the
            # protocol assumption remains clear when framing is added later.
            adc_value = (
                data[index]
                |
                (
                    data[index + 1]
                    << 8
                )
            )

            timestamp = (
                self.sample_index /
                self.sample_rate
            )

            self.sample_index += 1

            print(f"adc_val:{adc_value}")
            sample = MeasurementSample(
                timestamp=timestamp,
                voltage=float("nan"),
                current=float(adc_value)
            )

            self.sampleReady.emit(sample)
