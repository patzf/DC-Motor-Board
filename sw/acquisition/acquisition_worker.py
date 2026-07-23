import time
import numpy as np

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


    def __init__(self):

        super().__init__()

        self.connected = False

        self.running = False

        self.sample_rate = 1000

        self.timer = None

        self.timestamp = 0.0


    @Slot()
    def initialize(self):

        """
        Called after the worker is moved
        into its QThread.
        """

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.generate_samples
        )


    @Slot()
    def connect_device(self):

        """
        Simulation connection.

        Later:
        open USB CDC port here.
        """

        self.connected = True

        self.connectionChanged.emit(
            True
        )


    @Slot()
    def disconnect_device(self):

        self.stop()

        self.connected = False

        self.connectionChanged.emit(
            False
        )


    @Slot()
    def start(self):

        if not self.connected:

            self.errorOccurred.emit(
                "Device not connected"
            )

            return


        if self.timer is None:

            return


        interval = int(
            1000 /
            self.sample_rate
        )


        self.running = True

        self.timer.start(
            interval
        )

        self.acquisitionChanged.emit(
            True
        )


    @Slot()
    def stop(self):

        if self.timer:

            self.timer.stop()


        self.running = False

        self.acquisitionChanged.emit(
            False
        )


    @Slot(float)
    def set_motor_voltage(
        self,
        voltage
    ):

        """
        Later:

        Send command over USB CDC.

        """

        print(
            f"Motor voltage command: {voltage:.2f} V"
        )


    def generate_samples(self):

        """
        Simulation data source.

        This function will later be replaced
        by USB CDC packet parsing.
        """


        samples_per_tick = 10


        for _ in range(
            samples_per_tick
        ):

            self.timestamp += (
                1 /
                self.sample_rate
            )


            voltage = (
                5
                +
                2 *
                np.sin(
                    2 *
                    np.pi *
                    2 *
                    self.timestamp
                )
                +
                0.1 *
                np.random.randn()
            )


            current = (
                1
                +
                0.3 *
                np.sin(
                    2 *
                    np.pi *
                    5 *
                    self.timestamp
                )
                +
                0.03 *
                np.random.randn()
            )


            sample = MeasurementSample(
                timestamp=self.timestamp,
                voltage=voltage,
                current=current
            )


            self.sampleReady.emit(
                sample
            )
