import tkinter as tk
from tkinter import ttk
import math
import subprocess
import os
import re
import time
import tempfile

# PIL for better image handling
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: Pillow not installed. Install with: pip install pillow")


def get_monitors():
    """Detect available monitors with their positions."""
    monitors = []

    # Try xrandr first (works on X11 and XWayland, gives position info)
    try:
        result = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ' connected' in line:
                    # Parse: "DP-3 connected 1920x1080+0+600" or "DP-3 connected primary 1920x1080+1920+600"
                    match = re.search(r'^(\S+)\s+connected\s+(?:primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    if match:
                        monitors.append({
                            'name': match.group(1),
                            'width': int(match.group(2)),
                            'height': int(match.group(3)),
                            'x': int(match.group(4)),
                            'y': int(match.group(5))
                        })
            if monitors:
                # Sort by x position (left to right)
                monitors.sort(key=lambda m: (m['x'], m['y']))
                return monitors
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Try wlr-randr (Wayland - wlroots based compositors)
    try:
        result = subprocess.run(["wlr-randr"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            current_monitor = None
            current_pos = (0, 0)
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' ') and not line.startswith('\t'):
                    current_monitor = line.strip()
                elif current_monitor:
                    # Look for position
                    pos_match = re.search(r'Position:\s*(\d+),(\d+)', line)
                    if pos_match:
                        current_pos = (int(pos_match.group(1)), int(pos_match.group(2)))
                    # Look for current mode
                    if 'current' in line.lower():
                        match = re.search(r'(\d+)x(\d+)', line)
                        if match:
                            monitors.append({
                                'name': current_monitor,
                                'width': int(match.group(1)),
                                'height': int(match.group(2)),
                                'x': current_pos[0],
                                'y': current_pos[1]
                            })
                            current_monitor = None
                            current_pos = (0, 0)
            if monitors:
                monitors.sort(key=lambda m: (m['x'], m['y']))
                return monitors
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fallback: use tkinter (single monitor, no position)
    try:
        root = tk.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        monitors.append({
            'name': 'Primary Display',
            'width': width,
            'height': height,
            'x': 0,
            'y': 0
        })
    except:
        pass

    return monitors if monitors else [{'name': 'Default', 'width': 1920, 'height': 1080, 'x': 0, 'y': 0}]


class MonitorSelectDialog(tk.Toplevel):
    """Dialog to select which monitor to capture."""

    def __init__(self, parent, monitors, callback):
        super().__init__(parent)
        self.callback = callback
        self.monitors = monitors
        self.selected = None

        self.title("Select Monitor")
        self.geometry("450x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
        self.geometry(f"+{x}+{y}")

        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Select Monitor to Capture",
                 font=("Helvetica", 12, "bold")).pack(pady=(0, 15))

        self.monitor_var = tk.StringVar()

        for i, mon in enumerate(self.monitors):
            text = f"{mon['name']} ({mon['width']}x{mon['height']} at {mon['x']},{mon['y']})"
            rb = ttk.Radiobutton(frame, text=text, value=str(i),
                                variable=self.monitor_var)
            rb.pack(anchor=tk.W, pady=3)

        if self.monitors:
            self.monitor_var.set("0")

        ttk.Radiobutton(frame, text="All Monitors (Full Desktop)",
                       value="all", variable=self.monitor_var).pack(anchor=tk.W, pady=3)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(20, 0), fill=tk.X)

        ttk.Button(btn_frame, text="Cancel",
                  command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Capture",
                  command=self.confirm).pack(side=tk.RIGHT)

        self.bind('<Escape>', lambda e: self.cancel())
        self.bind('<Return>', lambda e: self.confirm())

    def confirm(self):
        selection = self.monitor_var.get()
        if selection == "all":
            self.selected = "all"
        else:
            self.selected = int(selection)
        self.destroy()
        self.callback(self.selected)

    def cancel(self):
        self.destroy()
        self.callback(None)


class ScreenshotMeasure(tk.Toplevel):
    """Take a screenshot and measure on it."""

    def __init__(self, parent, callback, monitor_selection=None, monitors=None):
        self.callback = callback
        self.parent = parent
        self.point1 = None
        # Use /tmp on Linux/macOS, fallback to tempfile for others
        if os.name == 'posix':
            self.screenshot_path = "/tmp/pixel_measure_screenshot.png"
        else:
            self.screenshot_path = os.path.join(tempfile.gettempdir(), "pixel_measure_screenshot.png")
        self.monitor_selection = monitor_selection
        self.monitors = monitors or []
        self.photo = None
        self.pil_image = None
        self.selected_monitor = None

        # Get selected monitor info
        if monitor_selection is not None and monitor_selection != "all":
            if monitors and monitor_selection < len(monitors):
                self.selected_monitor = monitors[monitor_selection]

        # Take screenshot first
        if not self.take_screenshot():
            print("Screenshot failed!")
            callback(None, None)
            return

        # Verify screenshot exists
        if not os.path.exists(self.screenshot_path):
            print(f"Screenshot file not found: {self.screenshot_path}")
            callback(None, None)
            return

        file_size = os.path.getsize(self.screenshot_path)
        if file_size < 1000:
            print(f"Screenshot file too small: {file_size} bytes")
            callback(None, None)
            return

        super().__init__(parent)
        self.title("Click two points to measure (ESC to cancel)")

        # Load and optionally crop image
        if not self.load_image():
            callback(None, None)
            return

        # Get dimensions for display
        if self.selected_monitor:
            display_w = self.selected_monitor['width']
            display_h = self.selected_monitor['height']
        else:
            display_w = self.winfo_screenwidth()
            display_h = self.winfo_screenheight()

        # Setup window
        self.geometry(f"{display_w}x{display_h}+0+0")
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.configure(bg='black')

        # Bind events
        self.bind('<Escape>', lambda e: self.cancel())
        self.bind('<Button-1>', self.on_click)
        self.bind('<Motion>', self.on_motion)

        # Canvas
        self.canvas = tk.Canvas(self, highlightthickness=0, cursor="crosshair",
                               bg='black', width=display_w, height=display_h)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Display screenshot
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo, tags="bg")

        # Instructions
        self.canvas.create_rectangle(10, 10, 450, 50, fill='black', stipple='gray50', tags="instr")
        self.instr_text = self.canvas.create_text(20, 30, anchor=tk.W,
            text="Click FIRST point (ESC to cancel)",
            font=("Helvetica", 16, "bold"), fill="yellow", tags="instr")

        self.focus_force()
        self.grab_set()

    def load_image(self):
        """Load screenshot and crop to selected monitor if needed."""
        if not HAS_PIL:
            print("Pillow is required for multi-monitor support")
            return False

        try:
            self.pil_image = Image.open(self.screenshot_path)
            full_w, full_h = self.pil_image.size
            print(f"Full screenshot: {full_w}x{full_h}")

            # Crop to selected monitor if not "all"
            if self.selected_monitor:
                mon = self.selected_monitor
                x1 = mon['x']
                y1 = mon['y']
                x2 = x1 + mon['width']
                y2 = y1 + mon['height']

                print(f"Cropping to monitor: {mon['name']} ({x1},{y1}) to ({x2},{y2})")

                # Ensure crop region is within image bounds
                x1 = max(0, min(x1, full_w))
                y1 = max(0, min(y1, full_h))
                x2 = max(0, min(x2, full_w))
                y2 = max(0, min(y2, full_h))

                self.pil_image = self.pil_image.crop((x1, y1, x2, y2))
                crop_w, crop_h = self.pil_image.size
                print(f"Cropped image: {crop_w}x{crop_h}")

            self.photo = ImageTk.PhotoImage(self.pil_image)
            return True

        except Exception as e:
            print(f"Image load error: {e}")
            return False

    def take_screenshot(self):
        """Take screenshot of full desktop."""
        # Remove old screenshot
        if os.path.exists(self.screenshot_path):
            os.remove(self.screenshot_path)

        # Use gnome-screenshot (captures all monitors)
        try:
            result = subprocess.run(
                ["gnome-screenshot", "-f", self.screenshot_path],
                capture_output=True, timeout=10
            )
            time.sleep(0.3)
            if os.path.exists(self.screenshot_path):
                print(f"Screenshot saved: {self.screenshot_path}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"gnome-screenshot failed: {e}")

        # Try grim (Wayland)
        try:
            result = subprocess.run(
                ["grim", self.screenshot_path],
                capture_output=True, timeout=10
            )
            time.sleep(0.3)
            if os.path.exists(self.screenshot_path):
                print(f"Screenshot saved with grim: {self.screenshot_path}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"grim failed: {e}")

        # Try scrot (X11)
        try:
            result = subprocess.run(
                ["scrot", self.screenshot_path],
                capture_output=True, timeout=10
            )
            time.sleep(0.3)
            if os.path.exists(self.screenshot_path):
                print(f"Screenshot saved with scrot: {self.screenshot_path}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"scrot failed: {e}")

        print("No screenshot tool worked!")
        return False

    def on_click(self, event):
        x, y = event.x, event.y

        if self.point1 is None:
            self.point1 = (x, y)
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                   fill="red", outline="white", width=2, tags="marker")
            self.canvas.itemconfig(self.instr_text, text="Click SECOND point (ESC to cancel)")
        else:
            point2 = (x, y)
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                   fill="blue", outline="white", width=2, tags="marker")
            self.canvas.delete("preview")
            self.canvas.create_line(self.point1[0], self.point1[1], x, y,
                                   fill="cyan", width=3, tags="final")
            self.after(200, lambda: self.finish(point2))

    def finish(self, point2):
        self.callback(self.point1, point2)
        self.cleanup()
        self.destroy()

    def on_motion(self, event):
        if self.point1:
            self.canvas.delete("preview")
            self.canvas.create_line(self.point1[0], self.point1[1],
                                   event.x, event.y,
                                   fill="cyan", width=2, dash=(5, 5), tags="preview")
            dx = event.x - self.point1[0]
            dy = event.y - self.point1[1]
            dist = math.sqrt(dx**2 + dy**2)
            self.canvas.delete("dist_label")
            mid_x = (self.point1[0] + event.x) / 2
            mid_y = (self.point1[1] + event.y) / 2
            self.canvas.create_text(mid_x, mid_y - 15,
                                   text=f"{dist:.1f} px",
                                   font=("Helvetica", 12, "bold"),
                                   fill="yellow", tags="dist_label")

    def cancel(self):
        self.cleanup()
        self.callback(None, None)
        self.destroy()

    def cleanup(self):
        try:
            if os.path.exists(self.screenshot_path):
                os.remove(self.screenshot_path)
        except:
            pass


class PixelMeasureTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Point2Point - Pixel Measurement Tool")
        self.root.geometry("550x800")
        self.root.minsize(450, 600)
        self.root.resizable(True, True)

        self.point1 = None
        self.point2 = None

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.monitors = get_monitors()
        self.selected_monitor = None

        self.dpi = 96
        self.base_font_size = 16

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Point2Point Measure Tool",
                                font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 10))

        instructions = ttk.Label(main_frame,
            text="Click 'Start Measuring' to capture screen.\nClick two points to measure. Press ESC to cancel.",
            justify=tk.CENTER, foreground="gray")
        instructions.pack(pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_btn = ttk.Button(btn_frame, text="Start Measuring",
                                    command=self.start_measuring)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.reset_btn = ttk.Button(btn_frame, text="Reset",
                                    command=self.reset_measurement)
        self.reset_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        self.status_var = tk.StringVar(value="Ready - Click 'Start Measuring' to begin")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                      font=("Helvetica", 10), foreground="blue")
        self.status_label.pack(pady=(0, 10))

        # Monitor info
        monitor_frame = ttk.LabelFrame(main_frame, text="Detected Monitors", padding="10")
        monitor_frame.pack(fill=tk.X, pady=(0, 15))

        for mon in self.monitors:
            ttk.Label(monitor_frame,
                     text=f"  {mon['name']}: {mon['width']}x{mon['height']} at ({mon['x']},{mon['y']})",
                     font=("Courier", 9)).pack(anchor=tk.W)

        # Points display
        points_frame = ttk.LabelFrame(main_frame, text="Selected Points", padding="10")
        points_frame.pack(fill=tk.X, pady=(0, 15))

        self.point1_var = tk.StringVar(value="Point 1: Not set")
        self.point2_var = tk.StringVar(value="Point 2: Not set")

        ttk.Label(points_frame, textvariable=self.point1_var).pack(anchor=tk.W)
        ttk.Label(points_frame, textvariable=self.point2_var).pack(anchor=tk.W)

        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 15))

        dpi_frame = ttk.Frame(settings_frame)
        dpi_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(dpi_frame, text="Screen DPI:").pack(side=tk.LEFT)
        self.dpi_var = tk.StringVar(value=str(self.dpi))
        dpi_entry = ttk.Entry(dpi_frame, textvariable=self.dpi_var, width=8)
        dpi_entry.pack(side=tk.LEFT, padx=(10, 0))

        font_frame = ttk.Frame(settings_frame)
        font_frame.pack(fill=tk.X)
        ttk.Label(font_frame, text="Base font size (px):").pack(side=tk.LEFT)
        self.font_var = tk.StringVar(value=str(self.base_font_size))
        font_entry = ttk.Entry(font_frame, textvariable=self.font_var, width=8)
        font_entry.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Button(settings_frame, text="Apply",
                   command=self.update_measurements).pack(pady=(10, 0))

        # Measurements
        measurements_frame = ttk.LabelFrame(main_frame, text="Measurements (All HTML Units)",
                                           padding="10")
        measurements_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(measurements_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(measurements_frame, orient="vertical", command=canvas.yview)
        self.measures_inner = ttk.Frame(canvas)

        self.measures_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.measures_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.measurement_labels = {}

        units = [
            ("Pixels (px)", "px", "Absolute pixel measurement"),
            ("Points (pt)", "pt", "1pt = 1/72 inch"),
            ("Em (em)", "em", "Relative to font-size (default 16px)"),
            ("Rem (rem)", "rem", "Relative to root font-size"),
            ("Percentage (%)", "%", "Relative to parent (% of screen width)"),
            ("Viewport Width (vw)", "vw", "1vw = 1% of viewport width"),
            ("Viewport Height (vh)", "vh", "1vh = 1% of viewport height"),
            ("Viewport Min (vmin)", "vmin", "1vmin = 1% of smaller dimension"),
            ("Viewport Max (vmax)", "vmax", "1vmax = 1% of larger dimension"),
            ("Centimeters (cm)", "cm", "Physical unit"),
            ("Millimeters (mm)", "mm", "Physical unit"),
            ("Inches (in)", "in", "Physical unit"),
            ("Picas (pc)", "pc", "1pc = 12pt"),
            ("Quarter-mm (Q)", "Q", "1Q = 1/4 millimeter"),
            ("Character (ch)", "ch", "Width of '0' (~0.5em)"),
            ("Ex height (ex)", "ex", "Height of 'x' (~0.5em)"),
        ]

        for name, unit, description in units:
            frame = ttk.Frame(self.measures_inner)
            frame.pack(fill=tk.X, pady=2)

            ttk.Label(frame, text=name, font=("Helvetica", 9, "bold"),
                     width=20, anchor=tk.W).pack(side=tk.LEFT)

            value_var = tk.StringVar(value="--")
            self.measurement_labels[unit] = value_var

            value_label = ttk.Label(frame, textvariable=value_var,
                                   font=("Courier", 10), width=15, anchor=tk.E)
            value_label.pack(side=tk.LEFT, padx=(5, 10))

            ttk.Label(frame, text=description, font=("Helvetica", 8),
                     foreground="gray").pack(side=tk.LEFT)

        self.diagonal_var = tk.StringVar(value="")
        ttk.Label(main_frame, textvariable=self.diagonal_var,
                 font=("Helvetica", 9), foreground="darkgreen").pack(pady=(10, 0))

    def start_measuring(self):
        self.start_btn.config(state=tk.DISABLED)

        if len(self.monitors) > 1:
            self.status_var.set("Select monitor...")
            MonitorSelectDialog(self.root, self.monitors, self.on_monitor_selected)
        else:
            self.on_monitor_selected(0 if self.monitors else "all")

    def on_monitor_selected(self, selection):
        if selection is None:
            self.status_var.set("Cancelled")
            self.start_btn.config(state=tk.NORMAL)
            return

        self.selected_monitor = selection
        self.status_var.set("Taking screenshot...")
        self.root.update()

        # Update screen dimensions based on selected monitor
        if selection != "all" and self.monitors and selection < len(self.monitors):
            self.screen_width = self.monitors[selection]['width']
            self.screen_height = self.monitors[selection]['height']

        self.root.withdraw()
        self.root.after(500, self.show_screenshot_overlay)

    def show_screenshot_overlay(self):
        ScreenshotMeasure(self.root, self.on_measurement_complete,
                         self.selected_monitor, self.monitors)

    def on_measurement_complete(self, point1, point2):
        self.root.deiconify()
        self.start_btn.config(state=tk.NORMAL)

        if point1 is None or point2 is None:
            self.status_var.set("Measurement cancelled or failed")
            return

        self.point1 = point1
        self.point2 = point2
        self.point1_var.set(f"Point 1: ({point1[0]}, {point1[1]})")
        self.point2_var.set(f"Point 2: ({point2[0]}, {point2[1]})")
        self.status_var.set("Measurement complete!")

        self.calculate_measurements()

    def calculate_measurements(self):
        if not self.point1 or not self.point2:
            return

        try:
            self.dpi = float(self.dpi_var.get())
            self.base_font_size = float(self.font_var.get())
        except ValueError:
            self.dpi = 96
            self.base_font_size = 16

        x1, y1 = self.point1
        x2, y2 = self.point2

        dx = x2 - x1
        dy = y2 - y1
        distance_px = math.sqrt(dx**2 + dy**2)

        self.diagonal_var.set(f"Δx: {abs(dx)}px | Δy: {abs(dy)}px | Diagonal: {distance_px:.2f}px")

        measurements = {}

        measurements["px"] = f"{distance_px:.2f} px"
        measurements["pt"] = f"{distance_px * 0.75:.2f} pt"
        measurements["pc"] = f"{distance_px * 0.75 / 12:.4f} pc"
        measurements["in"] = f"{distance_px / self.dpi:.4f} in"
        measurements["cm"] = f"{distance_px / self.dpi * 2.54:.4f} cm"
        measurements["mm"] = f"{distance_px / self.dpi * 25.4:.4f} mm"
        measurements["Q"] = f"{distance_px / self.dpi * 25.4 * 4:.4f} Q"

        measurements["em"] = f"{distance_px / self.base_font_size:.4f} em"
        measurements["rem"] = f"{distance_px / self.base_font_size:.4f} rem"
        measurements["ch"] = f"{distance_px / (self.base_font_size * 0.5):.4f} ch"
        measurements["ex"] = f"{distance_px / (self.base_font_size * 0.5):.4f} ex"

        measurements["vw"] = f"{distance_px / self.screen_width * 100:.4f} vw"
        measurements["vh"] = f"{distance_px / self.screen_height * 100:.4f} vh"
        measurements["%"] = f"{distance_px / self.screen_width * 100:.4f} %"

        vmin = min(self.screen_width, self.screen_height)
        vmax = max(self.screen_width, self.screen_height)
        measurements["vmin"] = f"{distance_px / vmin * 100:.4f} vmin"
        measurements["vmax"] = f"{distance_px / vmax * 100:.4f} vmax"

        for unit, value in measurements.items():
            if unit in self.measurement_labels:
                self.measurement_labels[unit].set(value)

    def update_measurements(self):
        if self.point1 and self.point2:
            self.calculate_measurements()

    def reset_measurement(self):
        self.point1 = None
        self.point2 = None
        self.point1_var.set("Point 1: Not set")
        self.point2_var.set("Point 2: Not set")
        self.status_var.set("Ready - Click 'Start Measuring' to begin")
        self.diagonal_var.set("")

        for unit in self.measurement_labels:
            self.measurement_labels[unit].set("--")

        self.start_btn.config(state=tk.NORMAL)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    print("Starting Pixel Measurement Tool...")
    print(f"Pillow available: {HAS_PIL}")
    app = PixelMeasureTool()
    app.run()
