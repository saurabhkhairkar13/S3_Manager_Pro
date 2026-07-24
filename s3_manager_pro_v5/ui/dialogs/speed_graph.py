"""Transfer Speed Graph — real-time line chart showing download/upload speed."""
import time
import tkinter as tk
import customtkinter as ctk
from collections import deque
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME
from s3_manager_pro_v5.utils.formatting import format_size


class SpeedGraph(ctk.CTkFrame):
    """Real-time speed graph widget using tkinter Canvas."""

    def __init__(self, parent, app, width=500, height=200):
        super().__init__(parent, width=width, height=height, corner_radius=8)
        self.app = app
        self.pack_propagate(False)

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        # Data storage (last 60 data points = 60 seconds)
        self.max_points = 60
        self.speed_data = deque(maxlen=self.max_points)  # bytes/sec
        self.time_data = deque(maxlen=self.max_points)

        # Canvas
        self.canvas = tk.Canvas(self, width=width - 20, height=height - 40,
                                bg=colors["surface"], highlightthickness=0)
        self.canvas.pack(padx=10, pady=(5, 0))

        # Labels
        self.speed_label = ctk.CTkLabel(self, text="Speed: 0 B/s",
                                        font=ctk.CTkFont(size=11),
                                        text_color=colors["text_secondary"])
        self.speed_label.pack(pady=(2, 5))

        self._running = False
        self._canvas_width = width - 20
        self._canvas_height = height - 40

    def start(self):
        """Start updating the graph."""
        self._running = True
        self._update()

    def stop(self):
        """Stop updating."""
        self._running = False

    def add_data_point(self, bytes_per_second: float):
        """Add a speed measurement."""
        self.speed_data.append(bytes_per_second)
        self.time_data.append(time.time())

    def _update(self):
        """Redraw the graph."""
        if not self._running:
            return

        self._draw()
        self.after(1000, self._update)  # Update every second

    def _draw(self):
        """Draw the speed graph."""
        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME
        self.canvas.delete("all")

        w = self._canvas_width
        h = self._canvas_height

        if len(self.speed_data) < 2:
            # Draw empty state
            self.canvas.create_text(w // 2, h // 2, text="Waiting for data...",
                                    fill=colors["text_secondary"], font=("Segoe UI", 10))
            return

        # Find max speed for scaling
        max_speed = max(self.speed_data) if self.speed_data else 1
        if max_speed == 0:
            max_speed = 1

        # Draw grid lines
        for i in range(5):
            y = int(h * i / 4)
            self.canvas.create_line(0, y, w, y, fill=colors["border"], dash=(2, 4))
            label_speed = max_speed * (1 - i / 4)
            self.canvas.create_text(5, y + 8, text=f"{format_size(int(label_speed))}/s",
                                    fill=colors["text_secondary"], font=("Segoe UI", 7),
                                    anchor="w")

        # Draw speed line
        points = []
        data_list = list(self.speed_data)
        step_x = w / (self.max_points - 1)

        for i, speed in enumerate(data_list):
            x = int(i * step_x)
            y = int(h - (speed / max_speed) * (h - 10))
            points.append((x, y))

        # Draw filled area
        if len(points) >= 2:
            fill_points = [(points[0][0], h)] + points + [(points[-1][0], h)]
            flat_fill = [coord for point in fill_points for coord in point]
            self.canvas.create_polygon(flat_fill, fill=colors["primary"] + "30",
                                       outline="", smooth=True)

            # Draw line
            flat_points = [coord for point in points for coord in point]
            self.canvas.create_line(flat_points, fill=colors["primary"],
                                    width=2, smooth=True)

            # Current speed indicator (last point)
            last_x, last_y = points[-1]
            self.canvas.create_oval(last_x - 4, last_y - 4, last_x + 4, last_y + 4,
                                    fill=colors["primary"], outline="")

        # Update label
        current_speed = data_list[-1] if data_list else 0
        avg_speed = sum(data_list) / len(data_list) if data_list else 0
        peak_speed = max(data_list) if data_list else 0

        self.speed_label.configure(
            text=f"Current: {format_size(int(current_speed))}/s │ "
                 f"Avg: {format_size(int(avg_speed))}/s │ "
                 f"Peak: {format_size(int(peak_speed))}/s"
        )


class SpeedGraphDialog:
    """Dialog showing the real-time speed graph."""

    def __init__(self, parent, app):
        self.app = app
        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("📈 Transfer Speed Graph")
        self.win.geometry("560x360")
        self.win.transient(parent)
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        ctk.CTkLabel(self.win, text="📈 Real-Time Transfer Speed",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(10, 5))

        # Speed graph widget
        self.graph = SpeedGraph(self.win, app, width=520, height=220)
        self.graph.pack(padx=20, pady=5)

        # Register with app for speed updates
        if not hasattr(app, '_speed_graphs'):
            app._speed_graphs = []
        app._speed_graphs.append(self.graph)

        self.graph.start()

        # Close button
        ctk.CTkButton(self.win, text="Close", width=70, height=28,
                      corner_radius=6, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self._close).pack(pady=(5, 10))

        self.win.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self):
        self.graph.stop()
        if hasattr(self.app, '_speed_graphs') and self.graph in self.app._speed_graphs:
            self.app._speed_graphs.remove(self.graph)
        self.win.destroy()
