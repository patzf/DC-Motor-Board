from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget
)

from PySide6.QtGui import (
    QIcon
)

from PySide6.QtCore import (
    Qt
)

from gui.live_tab import LiveTab
from gui.analysis_tab import AnalysisTab


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "DC Motor Identification Tool"
        )

        self.resize(
            1400,
            900
        )


        self.create_tabs()

        self.create_layout()



    def create_tabs(self):

        self.tabs = QTabWidget()


        self.live_tab = LiveTab()

        self.analysis_tab = AnalysisTab()


        try:

            live_icon = QIcon(
                "resources/icons/live.svg"
            )

            motor_icon = QIcon(
                "resources/icons/motor_id.svg"
            )


            self.tabs.addTab(
                self.live_tab,
                live_icon,
                "Live Measurement"
            )


            self.tabs.addTab(
                self.analysis_tab,
                motor_icon,
                "Motor Identification"
            )


        except Exception:

            # fallback if icons are not available

            self.tabs.addTab(
                self.live_tab,
                "Live Measurement"
            )


            self.tabs.addTab(
                self.analysis_tab,
                "Motor Identification"
            )



    def create_layout(self):

        self.setCentralWidget(
            self.tabs
        )



    def closeEvent(
        self,
        event
    ):

        """
        Clean shutdown.

        Stops acquisition thread
        before closing application.
        """


        if hasattr(
            self.live_tab,
            "controller"
        ):

            self.live_tab.controller.shutdown()


        event.accept()
