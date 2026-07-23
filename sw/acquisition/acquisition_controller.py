import numpy as np

from PySide6.QtCore import (
    QObject,
    Signal,
    QThread
)

from acquisition.acquisition_worker import AcquisitionWorker
from acquisition.ring_buffer import RingBuffer


class AcquisitionController(QObject):

    connectionChanged = Signal(bool)

    acquisitionChanged = Signal(bool)

    errorOccurred = Signal(str)

    connectRequest = Signal()

    disconnectRequest = Signal()

    startRequest = Signal()

    stopRequest = Signal()

    voltageRequest = Signal(float)


    def __init__(self, parent=None):

        super().__init__(parent)

        self.connected = False

        self.pending_start = False

        self.sample_rate = 1000


        buffer_size = (
            self.sample_rate *
            60
        )


        self.time_buffer = RingBuffer(
            buffer_size
        )

        self.voltage_buffer = RingBuffer(
            buffer_size
        )

        self.current_buffer = RingBuffer(
            buffer_size
        )


        self.thread = QThread(
            self
        )


        self.worker = AcquisitionWorker()


        self.worker.moveToThread(
            self.thread
        )


        self.connectRequest.connect(
            self.worker.connect_device
        )

        self.disconnectRequest.connect(
            self.worker.disconnect_device
        )

        self.startRequest.connect(
            self.worker.start
        )

        self.stopRequest.connect(
            self.worker.stop
        )

        self.voltageRequest.connect(
            self.worker.set_motor_voltage
        )


        self.thread.started.connect(
            self.worker.initialize
        )


        self.worker.sampleReady.connect(
            self.process_sample
        )


        self.worker.connectionChanged.connect(
            self.connection_state_changed
        )


        self.worker.acquisitionChanged.connect(
            self.acquisitionChanged
        )


        self.worker.errorOccurred.connect(
            self.errorOccurred
        )


        self.thread.start()



    def start(self):

        if not self.connected:

            self.pending_start = True

            self.connectRequest.emit()

            return


        self.startRequest.emit()



    def stop(self):

        self.pending_start = False

        self.stopRequest.emit()



    def connection_state_changed(
        self,
        connected
    ):

        self.connected = connected

        self.connectionChanged.emit(
            connected
        )


        if connected and self.pending_start:

            self.pending_start = False

            self.startRequest.emit()



    def disconnect_device(self):

        self.pending_start = False

        self.disconnectRequest.emit()



    def set_motor_voltage(
        self,
        voltage
    ):

        self.voltageRequest.emit(
            voltage
        )



    def process_sample(
        self,
        sample
    ):

        self.time_buffer.append(
            sample.timestamp
        )

        self.voltage_buffer.append(
            sample.voltage
        )

        self.current_buffer.append(
            sample.current
        )



    def get_data(
        self,
        history_seconds
    ):

        t = self.time_buffer.get()

        v = self.voltage_buffer.get()

        i = self.current_buffer.get()


        if len(t) == 0:

            return (
                np.array([]),
                np.array([]),
                np.array([])
            )


        mask = (
            t >
            t[-1] -
            history_seconds
        )


        return (
            t[mask],
            v[mask],
            i[mask]
        )



    def shutdown(self):

        self.stopRequest.emit()

        self.thread.quit()

        self.thread.wait()
