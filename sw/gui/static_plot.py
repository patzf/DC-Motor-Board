import pyqtgraph as pg

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QFont


class StaticPlotWidget(QWidget):

    def __init__(self, title, unit):
        super().__init__()

        self.plot_widget = pg.PlotWidget()

        self.curve = None

        self.configure_plot(
            title,
            unit
        )

        self.create_curve()

        self.data_x = []
        self.data_y = []

        layout = QVBoxLayout()

        layout.addWidget(
            self.plot_widget
        )

        self.setLayout(
            layout
        )


    def configure_plot(self, title, unit):

        self.plot_widget.setBackground(
            "k"
        )

        self.plot_widget.showGrid(
            x=True,
            y=True,
            alpha=0.3
        )

        self.plot_widget.setLabel(
            "left",
            title,
            units=unit,
            color="white",
            **{
                "font-size": "18pt"
            }
        )

        self.plot_widget.setLabel(
            "bottom",
            "Time",
            units="s",
            color="white",
            **{
                "font-size": "18pt"
            }
        )

        self.plot_widget.getPlotItem().layout.setContentsMargins(
            50,
            15,
            20,
            40
        )

        tick_font = QFont(
            "Arial",
            12
        )

        for axis_name in [
            "left",
            "bottom"
        ]:

            axis = self.plot_widget.getAxis(
                axis_name
            )

            axis.setTickFont(
                tick_font
            )

            axis.setTextPen(
                pg.mkPen(
                    "white"
                )
            )

        self.plot_widget.getViewBox().setBorder(
            pg.mkPen(
                "white",
                width=2
            )
        )

        # Initial fixed experiment range

        self.plot_widget.setXRange(
            0,
            5,
            padding=0
        )

        self.plot_widget.setYRange(
            0,
            3000,
            padding=0
        )


    def create_curve(self):

        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(
                width=3
            )
        )


    def load_data(self, x, y):

        self.data_x = x
        self.data_y = y

        self.curve.setData(
            self.data_x,
            self.data_y
        )


    def clear(self):

        self.curve.clear()

        self.data_x = []
        self.data_y = []
