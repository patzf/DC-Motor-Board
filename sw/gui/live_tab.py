from PySide6.QtCore import QTimer

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox
)

from acquisition.acquisition_controller import (
    AcquisitionController
)

from gui.live_plot import (
    LivePlotWidget
)


class LiveTab(QWidget):

    def __init__(self):

        super().__init__()

        self.history_seconds = 5

        self.controller = AcquisitionController()

        self.create_widgets()

        self.create_layout()

        self.connect_signals()

        self.create_display_timer()


    def create_widgets(self):

        self.voltage_plot = LivePlotWidget(
            "Motor Voltage",
            "V",
            "b"
        )


        self.current_plot = LivePlotWidget(
            "Motor Current",
            "ADC",
            "r"
        )


        self.acquire_button = QPushButton(
            "Start Acquisition"
        )


        self.history_select = QComboBox()

        self.history_select.addItems(
            [
                "1 s",
                "2 s",
                "5 s",
                "10 s",
                "30 s",
                "60 s"
            ]
        )


        self.history_select.setCurrentText(
            "5 s"
        )


        self.serial_port = QComboBox()

        self.serial_port.setMinimumWidth(
            120
        )


        self.refresh_ports_button = QPushButton(
            "Refresh Ports"
        )


        self.baudrate = QSpinBox()

        self.baudrate.setRange(
            1200,
            3000000
        )

        self.baudrate.setSingleStep(
            1200
        )

        self.baudrate.setValue(
            460800
        )


        self.voltage_command = QDoubleSpinBox()

        self.voltage_command.setRange(
            -24,
            24
        )

        self.voltage_command.setDecimals(
            2
        )

        self.voltage_command.setSingleStep(
            0.1
        )


        self.voltage_command.setValue(
            0
        )


        self.voltage_button = QPushButton(
            "Set Voltage"
        )


    def create_layout(self):

        layout = QVBoxLayout()


        layout.addWidget(
            self.voltage_plot
        )


        layout.addWidget(
            self.current_plot
        )


        controls = QHBoxLayout()


        controls.addWidget(
            self.acquire_button
        )


        controls.addWidget(
            QLabel(
                "History:"
            )
        )


        controls.addWidget(
            self.history_select
        )


        controls.addWidget(
            QLabel(
                "Serial Port:"
            )
        )


        controls.addWidget(
            self.serial_port
        )


        controls.addWidget(
            self.refresh_ports_button
        )


        controls.addWidget(
            QLabel(
                "Baud:"
            )
        )


        controls.addWidget(
            self.baudrate
        )


        controls.addStretch()


        controls.addWidget(
            QLabel(
                "Motor Voltage:"
            )
        )


        controls.addWidget(
            self.voltage_command
        )


        controls.addWidget(
            self.voltage_button
        )


        layout.addLayout(
            controls
        )


        self.setLayout(
            layout
        )


    def connect_signals(self):

        self.acquire_button.clicked.connect(
            self.toggle_acquisition
        )


        self.voltage_button.clicked.connect(
            self.set_voltage
        )


        self.history_select.currentTextChanged.connect(
            self.change_history
        )


        self.serial_port.currentTextChanged.connect(
            self.serial_port_changed
        )


        self.baudrate.valueChanged.connect(
            self.baudrate_changed
        )


        self.refresh_ports_button.clicked.connect(
            self.controller.refresh_ports
        )


        self.controller.acquisitionChanged.connect(
            self.acquisition_changed
        )


        self.controller.errorOccurred.connect(
            self.show_error
        )


        self.controller.portsChanged.connect(
            self.update_ports
        )


        self.controller.refresh_ports()


    def create_display_timer(self):

        self.display_timer = QTimer(
            self
        )


        self.display_timer.setInterval(
            33
        )


        self.display_timer.timeout.connect(
            self.update_display
        )


        self.display_timer.start()


    def toggle_acquisition(self):

        if (
            self.acquire_button.text()
            ==
            "Start Acquisition"
        ):

            self.controller.start()

        else:

            self.controller.stop()


    def acquisition_changed(
        self,
        running
    ):

        if running:

            self.acquire_button.setText(
                "Stop Acquisition"
            )

        else:

            self.acquire_button.setText(
                "Start Acquisition"
            )


    def update_ports(self, ports):

        current_port = self.serial_port.currentText()

        self.serial_port.blockSignals(True)

        self.serial_port.clear()
        self.serial_port.addItems(ports)

        if current_port in ports:
            self.serial_port.setCurrentText(current_port)

        elif ports:
            self.serial_port.setCurrentIndex(0)

        self.serial_port.blockSignals(False)

        if self.serial_port.currentText():
            self.serial_port_changed(
                self.serial_port.currentText()
            )


    def serial_port_changed(self, port):

        if port:
            self.controller.set_serial_config(
                port,
                self.baudrate.value()
            )


    def baudrate_changed(self, baudrate):

        if self.serial_port.currentText():
            self.controller.set_serial_config(
                self.serial_port.currentText(),
                baudrate
            )


    def show_error(self, message):

        print(
            f"Acquisition error: {message}"
        )


    def change_history(
        self,
        value
    ):

        self.history_seconds = int(
            value.split()[0]
        )


    def set_voltage(self):

        self.controller.set_motor_voltage(
            self.voltage_command.value()
        )


    def update_display(self):

        t, voltage, current = self.controller.get_data(
            self.history_seconds
        )


        if len(t) == 0:

            return


        t_v, voltage = self.decimate(
            t,
            voltage
        )


        t_i, current = self.decimate(
            t,
            current
        )


        # The STM32 currently provides only motor-current ADC samples.
        # The voltage channel is retained in the GUI but is intentionally
        # not populated with simulated data.
        self.current_plot.update_data(
            t_i,
            current,
            self.history_seconds
        )


        # Keep the existing voltage plot/widget.  NaN values from the
        # live worker produce no visible simulated voltage trace.
        self.voltage_plot.update_data(
            t_v,
            voltage,
            self.history_seconds
        )


    def decimate(
        self,
        x,
        y,
        max_points=2000
    ):

        if len(x) <= max_points:

            return x, y


        step = (
            len(x)
            //
            max_points
        )


        return (
            x[::step],
            y[::step]
        )
