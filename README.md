# Point2Point

A cross-platform screen pixel measurement tool that allows you to measure distances between any two points on your screen and displays the result in all HTML/CSS supported units.

## Features

- **Screen-wide Measurement**: Measure pixels anywhere on your screen (browser, desktop, any application)
- **Multi-Monitor Support**: Select which monitor to capture on multi-monitor setups
- **All HTML/CSS Units**: Instantly converts pixel measurements to all CSS length units
- **Live Preview**: See distance in real-time as you move the cursor
- **Configurable Settings**: Adjust DPI and base font size for accurate conversions
- **Resizable Window**: Customize the application window size to your preference

## Supported Platforms

### Operating Systems

| OS | Status | Notes |
|----|--------|-------|
| Linux | Fully Supported | Primary development platform |
| macOS | Should Work | Requires screenshot tool (e.g., `screencapture`) |
| Windows | Not Tested | May require modifications |

### Display Protocols

| Protocol | Status | Screenshot Tool | Notes |
|----------|--------|-----------------|-------|
| Wayland (GNOME) | Fully Supported | `gnome-screenshot` | Recommended for GNOME desktop |
| Wayland (wlroots) | Supported | `grim` | For Sway, Hyprland, etc. |
| X11 | Fully Supported | `scrot`, `gnome-screenshot` | Works with any X11 desktop |
| XWayland | Supported | `gnome-screenshot`, `grim` | Hybrid environments |

## Supported CSS Units

| Unit | Description |
|------|-------------|
| `px` | Pixels (absolute) |
| `pt` | Points (1pt = 1/72 inch) |
| `pc` | Picas (1pc = 12pt) |
| `em` | Relative to element font-size |
| `rem` | Relative to root font-size |
| `%` | Percentage of screen width |
| `vw` | 1% of viewport width |
| `vh` | 1% of viewport height |
| `vmin` | 1% of smaller viewport dimension |
| `vmax` | 1% of larger viewport dimension |
| `cm` | Centimeters |
| `mm` | Millimeters |
| `in` | Inches |
| `Q` | Quarter-millimeters |
| `ch` | Width of "0" character |
| `ex` | Height of "x" character |

## Requirements

### Python Dependencies

- Python 3.6+
- Tkinter (usually included with Python)
- Pillow (`pip install pillow`)

### Screenshot Tools (at least one required)

**For Wayland (GNOME):**
```bash
# Fedora/RHEL
sudo dnf install gnome-screenshot

# Ubuntu/Debian
sudo apt install gnome-screenshot
```

**For Wayland (wlroots-based compositors):**
```bash
# Fedora/RHEL
sudo dnf install grim

# Ubuntu/Debian
sudo apt install grim

# Arch
sudo pacman -S grim
```

**For X11:**
```bash
# Fedora/RHEL
sudo dnf install scrot

# Ubuntu/Debian
sudo apt install scrot

# Arch
sudo pacman -S scrot
```

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/tatlilimon/point2point.git
cd point2point

# Install Python dependencies
pip install pillow

# Make executable (optional)
chmod +x pixel_measure.py

# Create a command alias (optional)
mkdir -p ~/.local/bin
ln -sf $(pwd)/pixel_measure.py ~/.local/bin/point2point

# Add to PATH if needed (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

### Quick Start

```bash
python3 pixel_measure.py
```

Or if you created the alias:

```bash
point2point
```

## Usage

1. Launch the application
2. Click **"Start Measuring"**
3. If you have multiple monitors, select which one to capture
4. Click the **first point** on the screenshot
5. Move cursor to see **live distance preview**
6. Click the **second point**
7. View measurements in **all CSS units**

Press **ESC** at any time to cancel measurement.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Screen DPI | 96 | Adjust for accurate physical unit conversions (cm, mm, in) |
| Base font size | 16px | Reference font size for em/rem calculations |

## Multi-Monitor Setup

Point2Point automatically detects all connected monitors and their positions. When you click "Start Measuring":

1. A dialog appears listing all detected monitors with their:
   - Name (e.g., DP-1, HDMI-1, eDP-1)
   - Resolution (e.g., 1920x1080)
   - Position (x, y coordinates)
2. Select a specific monitor or "All Monitors (Full Desktop)"
3. The screenshot will be cropped to the selected monitor

## Troubleshooting

### Screenshot appears gray/empty

- Ensure you have a screenshot tool installed (`gnome-screenshot`, `grim`, or `scrot`)
- On Wayland, `gnome-screenshot` is recommended for GNOME desktop
- Check terminal output for error messages

### Monitor detection not working

- Install `xrandr` (usually pre-installed on most Linux systems)
- For wlroots-based compositors, install `wlr-randr`

### Window doesn't appear fullscreen

- This may happen on some Wayland compositors
- Try using "All Monitors" option instead of a specific monitor

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

GPL-3.0 license