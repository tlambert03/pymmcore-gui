#!/usr/bin/env python3
# Project: ASI CRISP Control - Plot Panel
# License: BSD 3-clause

import numpy as np
from matplotlib.backends.backend_qt import FigureCanvasQT as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)


class PlotWorker(QRunnable):
    """Worker thread for background processing of plot data."""

    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Run the worker function and emit result."""
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class PlotPanel(QWidget):
    """A panel for creating plots and viewing CRISP data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Create thread pool for background tasks
        self.threadpool = QThreadPool()

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create plot area
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        # self.canvas.setMinimumSize(600, 400)
        layout.addWidget(self.canvas)

        # Create plot
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Z Position (μm)")
        self.ax.set_ylabel("Focus Score")
        self.figure.tight_layout()

        # Create buttons
        btn_layout = QHBoxLayout()

        self.plot_button = QPushButton("Plot Focus Curve")
        self.plot_button.clicked.connect(self.on_plot_clicked)
        btn_layout.addWidget(self.plot_button)

        self.save_button = QPushButton("Save Plot")
        self.save_button.clicked.connect(self.on_save_clicked)
        btn_layout.addWidget(self.save_button)

        self.open_button = QPushButton("Open Plot")
        self.open_button.clicked.connect(self.on_open_clicked)
        btn_layout.addWidget(self.open_button)

        layout.addLayout(btn_layout)

    def on_plot_clicked(self) -> None:
        """Generate and display a focus curve."""
        # Start background worker to collect data
        worker = PlotWorker(self.collect_focus_data)
        worker.signals.result.connect(self.update_plot)
        worker.signals.error.connect(self.show_error)

        # Show a message that data collection is starting
        QMessageBox.information(
            self,
            "Plot Focus Curve",
            "Starting data collection.\nThis may take a few moments.",
        )

        # Execute the worker
        self.threadpool.start(worker)

    def collect_focus_data(self):
        """Collect focus data by moving Z stage and measuring focus scores."""
        # This would interface with the real hardware in the actual implementation
        # For demo, generate sample data
        z_positions = np.linspace(-5, 5, 100)
        # Generate a sample Gaussian curve
        focus_scores = 100 * np.exp(-(z_positions**2) / 2) + 5 * np.random.randn(100)

        return {"z_positions": z_positions, "focus_scores": focus_scores}

    def update_plot(self, data) -> None:
        """Update the plot with new data."""
        # Clear previous plot
        self.ax.clear()

        # Plot new data
        self.ax.plot(data["z_positions"], data["focus_scores"], "b-")

        # Add labels and title
        self.ax.set_xlabel("Z Position (μm)")
        self.ax.set_ylabel("Focus Score")
        self.ax.set_title("CRISP Focus Curve")

        # Apply tight layout and redraw canvas
        self.figure.tight_layout()
        self.canvas.draw()

    def on_save_clicked(self) -> None:
        """Save the current plot data to a CSV file."""
        # Get file name from user
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Focus Curve Data", "", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                # Get plot data (in real implementation, would get from the actual data source)
                lines = self.ax.get_lines()
                if lines:
                    x_data = lines[0].get_xdata()
                    y_data = lines[0].get_ydata()

                    # Save to CSV
                    with open(file_path, "w") as f:
                        f.write("Z Position (μm),Focus Score\n")
                        for x, y in zip(x_data, y_data, strict=False):
                            f.write(f"{x},{y}\n")

                    QMessageBox.information(
                        self, "Save Successful", f"Data saved to {file_path}"
                    )
                else:
                    QMessageBox.warning(
                        self, "No Data", "No plot data available to save."
                    )
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Error saving data: {e!s}")

    def on_open_clicked(self) -> None:
        """Open a saved CSV file and plot the data."""
        # Get file name from user
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Focus Curve Data", "", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                # Create a worker to load and process the file
                worker = PlotWorker(self.load_csv_data, file_path)
                worker.signals.result.connect(self.update_plot)
                worker.signals.error.connect(self.show_error)

                # Execute the worker
                self.threadpool.start(worker)
            except Exception as e:
                QMessageBox.critical(self, "Open Error", f"Error opening file: {e!s}")

    def load_csv_data(self, file_path):
        """Load data from a CSV file."""
        z_positions = []
        focus_scores = []

        with open(file_path) as f:
            # Skip header
            next(f)

            # Read data
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    try:
                        z = float(parts[0])
                        score = float(parts[1])
                        z_positions.append(z)
                        focus_scores.append(score)
                    except ValueError:
                        pass

        return {
            "z_positions": np.array(z_positions),
            "focus_scores": np.array(focus_scores),
        }

    def show_error(self, error_msg) -> None:
        """Display an error message."""
        QMessageBox.critical(self, "Error", error_msg)
