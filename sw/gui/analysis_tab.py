from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel
)

import numpy as np

from gui.static_plot import StaticPlotWidget


class AnalysisTab(QWidget):

    def __init__(self):
        super().__init__()

        self.create_widgets()
        self.create_layout()

    def create_widgets(self):

        self.step_button = QPushButton(
            "Step Response"
        )

        self.step_button.clicked.connect(
            self.load_step_response
        )

        self.identify_button = QPushButton(
            "Identify Motor"
        )

        self.identify_button.clicked.connect(
            self.identify_motor
        )

        self.status_label = QLabel(
            "No experiment loaded"
        )

        self.plot = StaticPlotWidget(
            "Motor Step Response",
            "rpm"
        )


    def create_layout(self):

        layout = QVBoxLayout()

        controls = QHBoxLayout()

        controls.addWidget(
            self.step_button
        )

        controls.addWidget(
            self.identify_button
        )

        controls.addStretch()

        controls.addWidget(
            self.status_label
        )

        layout.addLayout(
            controls
        )

        layout.addWidget(
            self.plot
        )

        self.setLayout(
            layout
        )


    def load_step_response(self):

        # Temporary simulated data
        #
        # Later this will be replaced by:
        #
        # STM32 -> USB CDC -> StepResponseData

        t = np.linspace(
            0,
            5,
            500
        )

        speed = 3000 * (
            1 -
            np.exp(
                -t / 0.8
            )
        )

        self.plot.load_data(
            t,
            speed
        )

        self.status_label.setText(
            "Step response loaded"
        )


    def identify_motor(self):

        # Future:
        #
        # self.plot.data
        #
        # ->
        # GEKKO/scipy identification
        #
        # ->
        # R, L, J, b, K values

        self.status_label.setText(
            "Identification started..."
        )

        print(
            "Motor identification placeholder"
        )
