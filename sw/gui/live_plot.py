import pyqtgraph as pg

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QFont


class LivePlotWidget(QWidget):

    def __init__(self, title, unit, color):
        super().__init__()

        self.plot_widget = pg.PlotWidget()

        self.configure_plot(
            title,
            unit
        )

        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(
                color=color,
                width=1
            ),
            antialias=False
        )

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

        self.plot_widget.enableAutoRange(
            x=False,
            y=False
        )

        # Let PyQtGraph reduce points internally
        # while preserving peaks

        self.plot_widget.setDownsampling(
            auto=True,
            mode="peak"
        )


    def update_data(
        self,
        x,
        y,
        history_seconds
    ):

        if len(x) == 0:
            return

        self.curve.setData(
            x,
            y
        )

        current_time = x[-1]

        self.plot_widget.setXRange(
            current_time - history_seconds,
            current_time,
            padding=0
        )
