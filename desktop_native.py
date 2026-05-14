#!/usr/bin/env python3
"""Native desktop exporter for BAR map packages.

This intentionally avoids browser canvas export limits. The GUI is lightweight
Tkinter, while large image assets are generated with Pillow in a background
thread.
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tkinter import END, filedialog, messagebox, ttk
import tkinter as tk

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageTk


OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
PYMAPCONV_SOURCE_URL = "https://raw.githubusercontent.com/Beherith/springrts_smf_compiler/v0.6.3/src/pymapconv.py"
PYMAPCONV_VERSION_URL = "https://raw.githubusercontent.com/Beherith/springrts_smf_compiler/v0.6.3/src/version.py"
PREVIEW_WIDTH = 1200
PREVIEW_HEIGHT = 720
MASK_WATER_BODY = (0, 0, 255)
MASK_WATERWAY = (0, 0, 180)


class NativeExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BAR Map Generator - Native Desktop Exporter")
        self.root.geometry("1720x1220")
        self.root.minsize(1420, 980)
        self.worker: threading.Thread | None = None
        self.preview_image = None
        self.preview_bounds = None
        self.preview_rect = None
        self.preview_drag = None

        self.mode = tk.StringVar(value="OSM location")
        self.map_name = tk.StringVar(value="struempfelbach_native")
        self.location = tk.StringVar(value="Strümpfelbach")
        self.map_size = tk.StringVar(value="1024")
        self.players = tk.StringVar(value="4")
        self.area_km = tk.StringVar(value="4.0")
        self.height_scale = tk.StringVar(value="2.5")
        self.output_path = tk.StringVar(value=str(Path.home() / "struempfelbach_native.sdz"))
        self.bar_maps_path = tk.StringVar(value=str(detect_bar_maps_dir()))
        self.status = tk.StringVar(value="Ready.")
        self.progress = tk.DoubleVar(value=0)
        self.map_name.trace_add("write", self._sync_output_name)
        self.map_size.trace_add("write", self._sync_preview_selection)
        self.area_km.trace_add("write", self._sync_preview_selection)

        self._build_style()
        self._build_ui()

    def _build_style(self) -> None:
        self.root.configure(bg="#05070a")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#0b1118", foreground="#d7e2ea", fieldbackground="#131b24")
        style.configure("TFrame", background="#0b1118")
        style.configure("TLabel", background="#0b1118", foreground="#d7e2ea")
        style.configure("Header.TLabel", font=("Sans", 22, "bold"), foreground="#65b7ff")
        style.configure("Sub.TLabel", foreground="#95a8b6")
        style.configure("TButton", background="#16324a", foreground="#e8f4ff", padding=8)
        style.map("TButton", background=[("active", "#1e4d75")])
        style.configure("Accent.TButton", background="#b88a22", foreground="#05070a", font=("Sans", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#d9a62b")])
        style.configure(
            "TEntry",
            fieldbackground="#131b24",
            background="#131b24",
            foreground="#e8f4ff",
            insertcolor="#e8f4ff",
            selectbackground="#265b86",
            selectforeground="#ffffff",
        )
        style.map(
            "TEntry",
            fieldbackground=[("readonly", "#131b24"), ("disabled", "#0f151c"), ("focus", "#162331")],
            foreground=[("readonly", "#e8f4ff"), ("disabled", "#6f7f8c")],
        )
        style.configure(
            "TCombobox",
            fieldbackground="#131b24",
            background="#131b24",
            foreground="#e8f4ff",
            arrowcolor="#e8f4ff",
            selectbackground="#265b86",
            selectforeground="#ffffff",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#131b24"), ("disabled", "#0f151c"), ("focus", "#162331")],
            background=[("readonly", "#131b24"), ("active", "#1e4d75")],
            foreground=[("readonly", "#e8f4ff"), ("disabled", "#6f7f8c")],
        )
        style.configure("Horizontal.TProgressbar", troughcolor="#101820", background="#65b7ff")

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=22)
        shell.pack(fill="both", expand=True)

        ttk.Label(shell, text="BAR Map Generator", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text="Native Linux exporter for large OSM-inspired BAR packages. No browser canvas limits.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 18))

        grid = ttk.Frame(shell)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        row = 0
        self._row(
            grid,
            row,
            "Generation mode",
            ttk.Combobox(grid, textvariable=self.mode, values=("OSM location", "Random procedural"), state="readonly"),
        )
        row += 1
        self._row(grid, row, "Map name", ttk.Entry(grid, textvariable=self.map_name))
        row += 1
        self._row(grid, row, "OSM place", ttk.Entry(grid, textvariable=self.location))
        row += 1
        self._row(grid, row, "Area width/height km", ttk.Entry(grid, textvariable=self.area_km))
        row += 1
        self._row(
            grid,
            row,
            "BAR size",
            ttk.Combobox(
                grid,
                textvariable=self.map_size,
                values=("512", "1024", "2048", "3072", "4096"),
                state="readonly",
            ),
        )
        row += 1
        self._row(
            grid,
            row,
            "Players",
            ttk.Combobox(
                grid,
                textvariable=self.players,
                values=("2", "4", "6", "8", "10", "12", "14", "16"),
                state="readonly",
            ),
        )
        row += 1
        self._row(
            grid,
            row,
            "Height scale",
            ttk.Combobox(
                grid,
                textvariable=self.height_scale,
                values=("1.0", "1.75", "2.5", "3.5", "5.0", "7.0"),
                state="readonly",
            ),
        )
        row += 1

        output_frame = ttk.Frame(grid)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_path).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(output_frame, text="Browse", command=self._choose_output).grid(row=0, column=1)
        self._row(grid, row, "Output .sdz", output_frame)
        row += 1

        bar_frame = ttk.Frame(grid)
        bar_frame.columnconfigure(0, weight=1)
        ttk.Entry(bar_frame, textvariable=self.bar_maps_path).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(bar_frame, text="Browse", command=self._choose_bar_folder).grid(row=0, column=1)
        self._row(grid, row, "BAR maps folder", bar_frame)

        note = ttk.Label(
            shell,
            text=(
                "This native exporter generates the source assets, runs PyMapConv, and packages a BAR-loadable .sdz. "
                "Large maps can take several minutes and use several GB of temporary disk space. "
                "The finished map is copied into the detected BAR maps folder automatically."
            ),
            style="Sub.TLabel",
            wraplength=820,
        )
        note.pack(fill="x", pady=(18, 10))

        ttk.Progressbar(shell, variable=self.progress, maximum=100).pack(fill="x", pady=(0, 8))
        ttk.Label(shell, textvariable=self.status).pack(anchor="w", pady=(0, 14))

        actions = ttk.Frame(shell)
        actions.pack(fill="x")
        ttk.Button(actions, text="Load OSM Preview", command=self._load_preview).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Generate Playable .sdz", style="Accent.TButton", command=self._start_export).pack(side="left")
        ttk.Button(actions, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=10)

        preview_frame = ttk.Frame(shell)
        preview_frame.pack(fill="x", pady=(16, 0))
        ttk.Label(preview_frame, text="OSM selection preview", style="Sub.TLabel").pack(anchor="w")
        self.preview_canvas = tk.Canvas(
            preview_frame,
            width=PREVIEW_WIDTH,
            height=PREVIEW_HEIGHT,
            bg="#111923",
            highlightthickness=1,
            highlightbackground="#314455",
        )
        self.preview_canvas.pack(anchor="w", pady=(6, 0))
        self.preview_canvas.bind("<ButtonPress-1>", self._preview_press)
        self.preview_canvas.bind("<B1-Motion>", self._preview_drag_motion)
        self.preview_canvas.bind("<ButtonRelease-1>", self._preview_release)

        log_frame = ttk.Frame(shell)
        log_frame.pack(fill="both", expand=True, pady=(18, 0))
        self.log = tk.Text(log_frame, bg="#05070a", fg="#b8c7d6", insertbackground="#e8f4ff", height=12)
        self.log.pack(fill="both", expand=True)

    def _row(self, parent: ttk.Frame, row: int, label: str, widget: tk.Widget) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 16))
        widget.grid(row=row, column=1, sticky="ew", pady=8)

    def _choose_output(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Save BAR map package",
            defaultextension=".sdz",
            filetypes=(("BAR map ZIP archive", "*.sdz"), ("All files", "*.*")),
            initialfile=Path(self.output_path.get()).name,
        )
        if filename:
            self.output_path.set(filename)

    def _sync_output_name(self, *_args) -> None:
        map_name = sanitize_name(self.map_name.get())
        current = Path(self.output_path.get()).expanduser()
        self.output_path.set(str(current.with_name(f"{map_name}.sdz")))

    def _sync_preview_selection(self, *_args) -> None:
        if self.preview_bounds and self.preview_rect:
            self._fit_preview_rect_to_bar_size()
            self._draw_preview_rect()

    def _choose_bar_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select BAR maps folder", initialdir=self.bar_maps_path.get())
        if folder:
            self.bar_maps_path.set(folder)

    def _open_output_folder(self) -> None:
        folder = Path(self.output_path.get()).expanduser().parent
        os.system(f'xdg-open "{folder}" >/dev/null 2>&1 &')

    def _start_export(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Export running", "A map export is already running.")
            return
        self.worker = threading.Thread(target=self._export_worker, daemon=True)
        self.worker.start()

    def _set_status(self, pct: float, msg: str) -> None:
        self.root.after(0, self.progress.set, pct)
        self.root.after(0, self.status.set, msg)
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg: str) -> None:
        self.log.insert(END, f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log.see(END)

    def _export_worker(self) -> None:
        try:
            config = ExportConfig(
                map_name=sanitize_name(self.map_name.get()),
                location=self.location.get().strip(),
                size=int(self.map_size.get()),
                players=int(self.players.get()),
                area_km=self._selected_area_km(),
                height_scale=float(self.height_scale.get()),
                output=Path(self.output_path.get()).expanduser().with_name(f"{sanitize_name(self.map_name.get())}.sdz"),
                mode=self.mode.get(),
                selection_bounds=self.get_selection_bounds(),
                bar_maps_dir=Path(self.bar_maps_path.get()).expanduser(),
            )
            export_native_package(config, self._set_status)
            self._set_status(100, f"Done: {config.output}")
            self.root.after(0, messagebox.showinfo, "Export complete", f"Created:\n{config.output}")
        except Exception as exc:
            self._set_status(0, f"Export failed: {exc}")
            self.root.after(0, messagebox.showerror, "Export failed", str(exc))

    def _load_preview(self) -> None:
        def worker() -> None:
            try:
                bounds = resolve_bounds(self.location.get().strip(), float(self.area_km.get()), self._set_status)
                image, image_bounds = load_osm_preview_image(bounds)
                photo = ImageTk.PhotoImage(image)
                self.root.after(0, self._show_preview, photo, image_bounds)
            except Exception as exc:
                self._set_status(0, f"Preview failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview(self, photo, image_bounds) -> None:
        self.preview_image = photo
        self.preview_bounds = image_bounds
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, image=photo, anchor="nw")
        self.preview_rect = None
        self._fit_preview_rect_to_bar_size()
        self._draw_preview_rect()

    def _selected_area_km(self) -> float:
        try:
            base_km = float(self.area_km.get())
        except ValueError:
            base_km = 4.0
        try:
            size = int(self.map_size.get())
        except ValueError:
            size = 1024
        return max(0.2, base_km * (size / 1024))

    def _fit_preview_rect_to_bar_size(self) -> None:
        if not self.preview_bounds:
            return
        west, south, east, north = self.preview_bounds
        preview_width_km = distance_km(north, west, north, east)
        preview_height_km = distance_km(north, west, south, west)
        if preview_width_km <= 0 or preview_height_km <= 0:
            return

        selected_km = self._selected_area_km()
        rect_w = min(PREVIEW_WIDTH * 0.92, max(24, PREVIEW_WIDTH * selected_km / preview_width_km))
        rect_h = min(PREVIEW_HEIGHT * 0.92, max(24, PREVIEW_HEIGHT * selected_km / preview_height_km))

        if self.preview_rect:
            cx = (self.preview_rect[0] + self.preview_rect[2]) / 2
            cy = (self.preview_rect[1] + self.preview_rect[3]) / 2
        else:
            cx = PREVIEW_WIDTH / 2
            cy = PREVIEW_HEIGHT / 2

        x0 = min(max(0, cx - rect_w / 2), PREVIEW_WIDTH - rect_w)
        y0 = min(max(0, cy - rect_h / 2), PREVIEW_HEIGHT - rect_h)
        self.preview_rect = [x0, y0, x0 + rect_w, y0 + rect_h]

    def _draw_preview_rect(self) -> None:
        self.preview_canvas.delete("selection")
        if not self.preview_rect:
            return
        self.preview_canvas.create_rectangle(
            *self.preview_rect,
            outline="#ff3b30",
            width=3,
            dash=(6, 4),
            fill="#ff3b30",
            stipple="gray25",
            tags="selection",
        )

    def _preview_press(self, event) -> None:
        if not self.preview_rect:
            return
        self.preview_drag = (event.x, event.y, list(self.preview_rect))

    def _preview_drag_motion(self, event) -> None:
        if not self.preview_drag:
            return
        sx, sy, rect = self.preview_drag
        dx, dy = event.x - sx, event.y - sy
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        x0 = min(max(0, rect[0] + dx), PREVIEW_WIDTH - width)
        y0 = min(max(0, rect[1] + dy), PREVIEW_HEIGHT - height)
        self.preview_rect = [x0, y0, x0 + width, y0 + height]
        self._draw_preview_rect()

    def _preview_release(self, _event) -> None:
        self.preview_drag = None

    def get_selection_bounds(self):
        if not self.preview_bounds or not self.preview_rect:
            return None
        west, south, east, north = self.preview_bounds
        x0, y0, x1, y1 = self.preview_rect
        selected_west = west + (east - west) * (x0 / PREVIEW_WIDTH)
        selected_east = west + (east - west) * (x1 / PREVIEW_WIDTH)
        selected_north = north + (south - north) * (y0 / PREVIEW_HEIGHT)
        selected_south = north + (south - north) * (y1 / PREVIEW_HEIGHT)
        return {
            "west": selected_west,
            "east": selected_east,
            "north": selected_north,
            "south": selected_south,
            "lat": (selected_north + selected_south) / 2,
            "lon": (selected_west + selected_east) / 2,
        }


class ExportConfig:
    def __init__(
        self,
        map_name: str,
        location: str,
        size: int,
        players: int,
        area_km: float,
        height_scale: float,
        output: Path,
        mode: str = "OSM location",
        selection_bounds=None,
        bar_maps_dir: Path | None = None,
    ) -> None:
        self.map_name = map_name
        self.location = location
        self.size = size
        self.players = players
        self.area_km = area_km
        self.height_scale = height_scale
        self.output = output
        self.mode = mode
        self.selection_bounds = selection_bounds
        self.bar_maps_dir = bar_maps_dir
        self.compile_min_height = -80.0
        self.compile_max_height = 360.0
        self.elevation_span_meters = 0.0
        self.relief_source = "unknown"


def sanitize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "native_osm_map"


def detect_bar_maps_dir() -> Path:
    candidates = [
        Path.home() / ".local/state/Beyond All Reason/maps",
        Path.home() / ".local/state/Beyond All Reason/data/maps",
        Path.home() / ".var/app/info.beyondallreason.bar/data/maps",
        Path.home() / ".spring/maps",
        Path.home() / "Documents/My Games/Spring/maps",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def install_to_bar_maps(sd7_path: Path, maps_dir: Path | None, status) -> None:
    target_dir = maps_dir or detect_bar_maps_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / sd7_path.name
    shutil.copy2(sd7_path, target)
    status(99, f"Installed map into BAR maps folder: {target}")


def synthetic_bounds():
    return {
        "south": 48.75,
        "west": 9.32,
        "north": 48.79,
        "east": 9.38,
        "lat": 48.77,
        "lon": 9.35,
    }


def create_synthetic_elevation_grid(bounds, grid_size: int):
    random.seed(int(time.time()))
    values = []
    seed = random.random() * 1000
    for y in range(grid_size):
        for x in range(grid_size):
            u = x / (grid_size - 1)
            v = y / (grid_size - 1)
            ridge = math.sin((u * 2.7 + v * 1.3 + seed) * math.pi) * 30
            rolling = noise(u * 8 + seed, v * 8 - seed) * 24
            detail = noise(u * 28 - seed, v * 28 + seed) * 9
            values.append(90 + ridge + rolling + detail)
    return {"grid_size": grid_size, "values": values}


def load_osm_preview_image(bounds):
    zoom = 13
    center_x, center_y = latlon_to_tile(bounds["lat"], bounds["lon"], zoom)
    tile_size = 256
    image = Image.new("RGB", (tile_size * 3, tile_size * 3), (18, 27, 36))
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            tx = center_x + dx
            ty = center_y + dy
            try:
                response = requests.get(
                    f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png",
                    headers={"User-Agent": "BAR Native Map Generator"},
                    timeout=15,
                )
                if response.ok:
                    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                        tmp.write(response.content)
                        tmp.flush()
                        tile = Image.open(tmp.name).convert("RGB")
                    image.paste(tile, ((dx + 1) * tile_size, (dy + 1) * tile_size))
            except Exception:
                pass
    preview = image.resize((PREVIEW_WIDTH, PREVIEW_HEIGHT), Image.Resampling.BILINEAR)
    west, north = tile_to_latlon(center_x - 1, center_y - 1, zoom)
    east, south = tile_to_latlon(center_x + 2, center_y + 2, zoom)
    return preview, (west, south, east, north)


def latlon_to_tile(lat: float, lon: float, zoom: int):
    lat_rad = math.radians(lat)
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_latlon(x: int, y: int, zoom: int):
    n = 2**zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def export_native_package(config: ExportConfig, status) -> None:
    if config.output.suffix.lower() != ".sdz":
        config.output = config.output.with_suffix(".sdz")
    config.output = config.output.with_name(f"{config.map_name}.sdz")
    map_units = config.size // 64
    if config.mode == "Random procedural":
        bounds = synthetic_bounds()
    else:
        bounds = config.selection_bounds or resolve_bounds(config.location, config.area_km, status)

    with tempfile.TemporaryDirectory(prefix="bar-native-export-") as tmp:
        root = Path(tmp)
        assets = root / "assets"
        assets.mkdir()

        if config.mode == "Random procedural":
            status(15, "Creating random procedural elevation...")
            elevation = create_synthetic_elevation_grid(bounds, grid_size=48)
            features = []
        else:
            status(15, "Sampling 64x64 elevation grid...")
            elevation = load_elevation_grid(bounds, grid_size=64, status=status)

            status(28, "Loading OSM features with fallback...")
            features = load_osm_features(bounds)

        status(38, "Generating base terrain...")
        base_height, base_texture = generate_base_maps(config, bounds, elevation, features)

        status(52, "Writing BAR heightmap, metalmap, grassmap and typemap...")
        write_heightmap(base_height, config.size, assets / "heightmap.bmp")
        metal_spots, start_positions = write_metalmap(config, base_height, assets / "metalmap.bmp")
        write_grassmap(config, base_height, assets / "grassmap.bmp")
        write_typemap(config, base_height, assets / "typemap.bmp")

        status(64, "Writing large texture asset natively...")
        texture_size = 512 * map_units
        base_texture.resize((texture_size, texture_size), Image.Resampling.BILINEAR).save(assets / "texture.bmp")

        status(76, "Writing normal, specular, minimap and splat assets...")
        Image.new("RGB", (texture_size, texture_size), (128, 128, 255)).save(assets / "normalmap.png")
        Image.new("RGB", (256 * map_units, 256 * map_units), (72, 72, 72)).save(assets / "specularmap.png")
        base_texture.resize((1024, 1024), Image.Resampling.BILINEAR).save(assets / "minimap.png")
        Image.new("RGBA", (max(2048, config.size // 2), max(2048, config.size // 2)), (255, 0, 0, 0)).save(
            assets / "splatmap.png"
        )

        status(82, "Writing map config and build scripts...")
        (root / "mapinfo.lua").write_text(generate_mapinfo(config, start_positions), encoding="utf-8")
        helper = root / "maphelper"
        helper.mkdir()
        (helper / "maphelper.lua").write_text("-- Native BAR Map Generator helper\n", encoding="utf-8")
        (root / "README.md").write_text(generate_readme(config, bounds, len(features)), encoding="utf-8")
        (root / "build.sh").write_text("#!/usr/bin/env bash\npython3 build_map.py\n", encoding="utf-8")
        (root / "build.bat").write_text("@echo off\r\npython build_map.py\r\n", encoding="utf-8")
        (root / "build_map.py").write_text(generate_build_script(config), encoding="utf-8")
        shutil.copy2(Path(__file__), root / "desktop_native.py")

        status(86, "Packaging source ZIP...")
        config.output.parent.mkdir(parents=True, exist_ok=True)
        source_zip = config.output.with_name(f"{config.output.stem}_source.zip")
        with zipfile.ZipFile(source_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as zf:
            for path in root.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(root).as_posix())

        status(90, "Compiling playable .sdz with PyMapConv...")
        final_sdz = compile_playable_sd7(root, config, status)
        shutil.copy2(final_sdz, config.output)
        install_to_bar_maps(config.output, config.bar_maps_dir, status)


def resolve_bounds(location: str, area_km: float, status):
    if not location:
        raise ValueError("OSM place is required.")
    status(5, f"Resolving location: {location}")
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": "BAR Native Map Generator"},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f"Location not found: {location}")
    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    half = max(0.2, area_km / 2)
    lat_delta = half / 111.32
    lon_delta = half / (111.32 * max(0.2, math.cos(math.radians(lat))))
    return {
        "south": lat - lat_delta,
        "west": lon - lon_delta,
        "north": lat + lat_delta,
        "east": lon + lon_delta,
        "lat": lat,
        "lon": lon,
    }


def load_elevation_grid(bounds, grid_size: int, status):
    points = []
    for y in range(grid_size):
        v = y / (grid_size - 1)
        lat = bounds["north"] + (bounds["south"] - bounds["north"]) * v
        for x in range(grid_size):
            u = x / (grid_size - 1)
            lon = bounds["west"] + (bounds["east"] - bounds["west"]) * u
            points.append((lat, lon))

    values: list[float] = []
    fallback_reason = None
    try:
        for i in range(0, len(points), 50):
            batch = points[i : i + 50]
            response = requests.get(
                "https://api.open-meteo.com/v1/elevation",
                params={
                    "latitude": ",".join(f"{p[0]:.6f}" for p in batch),
                    "longitude": ",".join(f"{p[1]:.6f}" for p in batch),
                },
                timeout=25,
            )
            response.raise_for_status()
            elevations = response.json().get("elevation")
            if not isinstance(elevations, list):
                raise ValueError("Elevation response missing elevation list")
            if len(elevations) != len(batch):
                raise ValueError(f"Elevation response returned {len(elevations)}/{len(batch)} samples")
            batch_values = [float(v) for v in elevations if isinstance(v, (int, float)) or str(v).replace(".", "", 1).replace("-", "", 1).isdigit()]
            if len(batch_values) != len(batch):
                raise ValueError("Elevation response contained non-numeric samples")
            values.extend(batch_values)
            status(15 + 10 * min(1, len(values) / len(points)), f"Elevation samples: {len(values)}/{len(points)}")
            time.sleep(0.1)
    except Exception as exc:
        fallback_reason = f"Open-Meteo elevation failed: {exc}"
        values = []

    if len(values) != len(points):
        fallback_reason = fallback_reason or f"Open-Meteo returned {len(values)}/{len(points)} samples"
        status(25, f"Elevation fallback: {fallback_reason}")
        random.seed(int(abs(bounds["lat"] * 1000 + bounds["lon"] * 1000)))
        values = []
        for y in range(grid_size):
            for x in range(grid_size):
                u = x / (grid_size - 1)
                v = y / (grid_size - 1)
                values.append(90 + math.sin((u * 2 + v) * math.pi) * 24 + noise(u * 8, v * 8) * 18)

    grid = create_elevation_grid(
        bounds=bounds,
        grid_size=grid_size,
        values=values,
        source="synthetic-fallback" if fallback_reason else "open-meteo",
        provider_name="Procedural synthetic relief" if fallback_reason else "Open-Meteo Elevation API",
        synthetic=bool(fallback_reason),
        fallback_reason=fallback_reason,
    )
    meta = grid["metadata"]
    status(
        26,
        f'Elevation source: {meta["provider_name"]}; grid {meta["grid_width"]}x{meta["grid_height"]}; '
        f'min/max {meta["min_elevation_m"]:.1f}/{meta["max_elevation_m"]:.1f} m'
    )
    return grid


def create_elevation_grid(bounds, grid_size: int, values: list[float], source: str, provider_name: str, synthetic: bool, fallback_reason: str | None):
    plain_bounds = {
        "south": bounds["south"],
        "west": bounds["west"],
        "north": bounds["north"],
        "east": bounds["east"],
    }
    finite_values = [v for v in values if math.isfinite(v)]
    metadata = {
        "source": source,
        "provider_name": provider_name,
        "bounds": plain_bounds,
        "grid_width": grid_size,
        "grid_height": grid_size,
        "sample_count": len(finite_values),
        "min_elevation_m": min(finite_values) if finite_values else 0.0,
        "max_elevation_m": max(finite_values) if finite_values else 0.0,
        "estimated_resolution_m_x": estimate_longitude_resolution_m(plain_bounds, grid_size),
        "estimated_resolution_m_y": estimate_latitude_resolution_m(plain_bounds, grid_size),
        "synthetic": synthetic,
        "fallback_reason": fallback_reason,
        "cache_key": create_elevation_cache_key(source, plain_bounds, grid_size, grid_size),
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "grid_size": grid_size,
        "grid_width": grid_size,
        "grid_height": grid_size,
        "values": values,
        "synthetic": synthetic,
        "metadata": metadata,
    }


def estimate_latitude_resolution_m(bounds, grid_height: int) -> float:
    if grid_height <= 1:
        return 0.0
    return abs(bounds["north"] - bounds["south"]) * 111320 / (grid_height - 1)


def estimate_longitude_resolution_m(bounds, grid_width: int) -> float:
    if grid_width <= 1:
        return 0.0
    mid_lat = (bounds["north"] + bounds["south"]) / 2
    return abs(bounds["east"] - bounds["west"]) * 111320 * math.cos(math.radians(mid_lat)) / (grid_width - 1)


def create_elevation_cache_key(source: str, bounds, grid_width: int, grid_height: int) -> str:
    return (
        f'{source}:{bounds["south"]:.6f}:{bounds["west"]:.6f}:'
        f'{bounds["north"]:.6f}:{bounds["east"]:.6f}:{grid_width}x{grid_height}'
    )


def load_osm_features(bounds):
    bbox = f'{bounds["south"]:.6f},{bounds["west"]:.6f},{bounds["north"]:.6f},{bounds["east"]:.6f}'
    query = f"""
        [out:json][timeout:20];
        (
            way["natural"~"water|wood|wetland|beach|sand|bare_rock"]({bbox});
            way["waterway"]({bbox});
            way["landuse"~"forest|grass|meadow|farmland|residential|industrial"]({bbox});
            way["highway"]({bbox});
        );
        out geom;
    """
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data={"data": query}, timeout=30)
            if response.ok:
                return response.json().get("elements", [])
        except Exception:
            pass
    return []


def generate_base_maps(config: ExportConfig, bounds, elevation, features):
    size = config.size
    metadata = elevation.get("metadata") or {}
    min_el = metadata.get("min_elevation_m", min(elevation["values"]))
    max_el = metadata.get("max_elevation_m", max(elevation["values"]))
    span = max(1, max_el - min_el)
    height_range = max(220.0, min(1400.0, span * config.height_scale))
    config.compile_min_height = -max(25.0, height_range * 0.08)
    config.compile_max_height = height_range
    config.elevation_span_meters = span
    config.relief_source = "real" if metadata.get("source") == "open-meteo" else metadata.get("source", "unknown")
    mask = rasterize_features(config, bounds, features)
    height_img = Image.new("L", (size, size))
    tex = Image.new("RGB", (size, size))
    hpx = height_img.load()
    tpx = tex.load()
    for y in range(size):
        v = y / (size - 1)
        for x in range(size):
            u = x / (size - 1)
            elev = sample_elevation(elevation, u, v)
            normalized = (elev - min_el) / span
            h = 24 + normalized * 218 + noise(x * 0.025, y * 0.025) * 3
            m = mask.getpixel((x, y))
            if m == MASK_WATER_BODY:
                h = min(h, 42)
            elif m == MASK_WATERWAY:
                h -= 10
            h = int(max(0, min(255, h)))
            hpx[x, y] = h
            tpx[x, y] = terrain_color(h, m)
    height_img = height_img.filter(ImageFilter.SMOOTH_MORE)
    return height_img, tex


def rasterize_features(config: ExportConfig, bounds, features):
    img = Image.new("RGB", (config.size, config.size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for el in features:
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        tags = el.get("tags") or {}
        color = feature_color(tags)
        if not color:
            continue
        pts = [project_point(config, bounds, p["lat"], p["lon"]) for p in geom]
        if tags.get("highway") or tags.get("waterway"):
            draw.line(pts, fill=color, width=max(2, config.size // 180), joint="curve")
        else:
            draw.polygon(pts, fill=color)
    return img


def feature_color(tags):
    if tags.get("waterway"):
        return MASK_WATERWAY
    if tags.get("natural") in {"water", "wetland"}:
        return MASK_WATER_BODY
    if tags.get("natural") == "wood" or tags.get("landuse") == "forest":
        return (0, 255, 0)
    if tags.get("highway"):
        return (0, 255, 255)
    if tags.get("landuse") in {"grass", "meadow", "farmland"}:
        return (255, 255, 0)
    if tags.get("natural") in {"beach", "sand"}:
        return (255, 0, 255)
    if tags.get("natural") == "bare_rock":
        return (255, 0, 0)
    return None


def project_point(config: ExportConfig, bounds, lat: float, lon: float):
    x = (lon - bounds["west"]) / max(0.000001, bounds["east"] - bounds["west"]) * config.size
    y = (bounds["north"] - lat) / max(0.000001, bounds["north"] - bounds["south"]) * config.size
    return (int(max(0, min(config.size - 1, x))), int(max(0, min(config.size - 1, y))))


def sample_elevation(grid, u: float, v: float) -> float:
    grid_width = grid.get("grid_width") or grid["grid_size"]
    grid_height = grid.get("grid_height") or grid["grid_size"]
    max_x = grid_width - 1
    max_y = grid_height - 1
    gx = u * max_x
    gy = v * max_y
    x0 = int(gx)
    y0 = int(gy)
    x1 = min(max_x, x0 + 1)
    y1 = min(max_y, y0 + 1)
    tx = gx - x0
    ty = gy - y0

    def at(x, y):
        return grid["values"][y * grid_width + x]

    a = at(x0, y0) * (1 - tx) + at(x1, y0) * tx
    b = at(x0, y1) * (1 - tx) + at(x1, y1) * tx
    return a * (1 - ty) + b * ty


def noise(x: float, y: float) -> float:
    n = math.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return (n - math.floor(n)) * 2 - 1


def terrain_color(height: int, mask):
    if height < 58 or mask in {MASK_WATER_BODY, MASK_WATERWAY}:
        return (26, 92, 143)
    if mask == (0, 255, 255):
        return (102, 101, 94)
    if mask == (0, 255, 0):
        return (50, 105, 64)
    if mask == (255, 255, 0):
        return (128, 139, 78)
    if mask == (255, 0, 255) or height < 66:
        return (194, 178, 125)
    if mask == (255, 0, 0) or height > 160:
        return (117, 113, 105)
    return (74, 134, 82)


def write_heightmap(base_height: Image.Image, size: int, path: Path) -> None:
    base_height.resize((size + 1, size + 1), Image.Resampling.BILINEAR).convert("RGB").save(path)


def write_metalmap(config: ExportConfig, height: Image.Image, path: Path):
    units = config.size // 64
    dim = 32 * units
    img = Image.new("RGB", (dim, dim), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    spots = []
    starts = []
    radius = config.size * 0.35
    cx = cy = config.size / 2
    for i in range(config.players):
        a = (i / config.players) * math.tau
        sx = int(cx + math.cos(a) * radius)
        sy = int(cy + math.sin(a) * radius)
        starts.append((sx, sy))
        for j in range(4):
            da = a + (j - 1.5) * 0.18
            dist = radius * (0.75 + j * 0.08)
            x = int(cx + math.cos(da) * dist)
            y = int(cy + math.sin(da) * dist)
            spots.append((max(0, min(config.size - 1, x)), max(0, min(config.size - 1, y))))
    scale = dim / config.size
    for x, y in spots:
        px = int(x * scale)
        py = int(y * scale)
        draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 0, 0))
    img.save(path)
    return spots, starts


def write_grassmap(config: ExportConfig, height: Image.Image, path: Path) -> None:
    units = config.size // 64
    dim = 16 * units
    height.resize((dim, dim), Image.Resampling.BILINEAR).point(lambda v: 160 if 64 < v < 150 else 0).convert("RGB").save(path)


def write_typemap(config: ExportConfig, height: Image.Image, path: Path) -> None:
    units = config.size // 64
    dim = 32 * units
    height.resize((dim, dim), Image.Resampling.BILINEAR).point(
        lambda v: 0 if v < 58 else 85 if v < 138 else 170 if v < 208 else 255
    ).convert("RGB").save(path)


def generate_mapinfo(config: ExportConfig, starts) -> str:
    def sx(x):
        return int(x * 8)

    def sz(y):
        return int(y * 8)

    teams = "\n".join(
        f"        [{i}] = {{ startpos = {{ x = {sx(x)}, z = {sz(y)} }} }},"
        for i, (x, y) in enumerate(starts)
    )
    return f"""return {{
    name = "{config.map_name}",
    shortname = "{config.map_name}",
    description = "Native generated BAR map",
    author = "BAR Native Map Generator",
    version = "1.0",
    maphardness = 100,
    gravity = 130,
    tidalStrength = 20,
    maxMetal = 1.0,
    extractorRadius = 80,
    voidWater = false,
    mapfile = "maps/{config.map_name}.smf",
    modtype = 3,
    teams = {{
{teams}
    }},
    startpostype = 2,
}}
"""


def generate_readme(config: ExportConfig, bounds, feature_count: int) -> str:
    return f"""# {config.map_name}

Native desktop export for Beyond All Reason.

- Size: {config.size}x{config.size}
- Players: {config.players}
- Location: {config.location}
- OSM feature count: {feature_count}

The native GUI already attempted to create the final `.sdz`. To rebuild from
this source package, run `python3 build_map.py`.
"""


def generate_build_script(config: ExportConfig) -> str:
    return f"""#!/usr/bin/env python3
from desktop_native import compile_playable_sd7, ExportConfig
from pathlib import Path

cfg = ExportConfig(
    map_name="{config.map_name}",
    location="{config.location}",
    size={config.size},
    players={config.players},
    area_km={config.area_km},
    height_scale={config.height_scale},
    output=Path("output/{config.map_name}.sdz"),
)
Path("output").mkdir(exist_ok=True)
result = compile_playable_sd7(Path("."), cfg, lambda pct, msg: print(msg))
cfg.output.write_bytes(result.read_bytes())
print(f"Created {{cfg.output}}")
"""


def compile_playable_sd7(root: Path, config: ExportConfig, status) -> Path:
    tools_dir = root / "tools"
    build_dir = root / "build"
    compiled_maps = build_dir / "compiled" / "maps"
    map_container = build_dir / f"{config.map_name}.sdd"
    map_container_maps = map_container / "maps"
    output_dir = build_dir / "output"
    output_smf = compiled_maps / f"{config.map_name}.smf"
    final_sdz = output_dir / f"{config.map_name}.sdz"
    log_path = config.output.with_suffix(".pymapconv.log")

    tools_dir.mkdir(exist_ok=True)
    compiled_maps.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pymapconv = ensure_pymapconv(tools_dir, status)
    prepare_pymapconv_runtime(root, tools_dir)

    full_cmd = [
        str(pymapconv),
        "-u",
        "-q",
        "1",
        "-x",
        f"{config.compile_max_height:.2f}",
        "-n",
        f"{config.compile_min_height:.2f}",
        "-a",
        str(root / "assets" / "heightmap.bmp"),
        "-m",
        str(root / "assets" / "metalmap.bmp"),
        "-t",
        str(root / "assets" / "texture.bmp"),
        "-l",
        str(root / "assets" / "normalmap.png"),
        "-z",
        str(root / "assets" / "specularmap.png"),
        "-p",
        str(root / "assets" / "minimap.png"),
        "-r",
        str(root / "assets" / "grassmap.bmp"),
        "-y",
        str(root / "assets" / "typemap.bmp"),
        "-o",
        str(output_smf),
    ]

    status(92, "Running PyMapConv...")
    result = run_pymapconv_command(root, full_cmd)
    combined_output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if pymapconv_source_cli_succeeded(result, output_smf, combined_output):
        result = subprocess.CompletedProcess(result.args, 0, result.stdout, result.stderr)

    if result.returncode != 0 and is_texture_compression_failure(combined_output):
        status(94, "Texture compression failed. Retrying PyMapConv with Linux single-thread fallback...")
        prepare_pymapconv_runtime(root, tools_dir)
        fallback_cmd = [
            str(pymapconv),
            "-u",
            "-q",
            "1",
            "-x",
            f"{config.compile_max_height:.2f}",
            "-n",
            f"{config.compile_min_height:.2f}",
            "-a",
            str(root / "assets" / "heightmap.bmp"),
            "-m",
            str(root / "assets" / "metalmap.bmp"),
            "-t",
            str(root / "assets" / "texture.bmp"),
            "-p",
            str(root / "assets" / "minimap.png"),
            "-o",
            str(output_smf),
        ]
        fallback_result = run_pymapconv_command(root, fallback_cmd)
        write_pymapconv_log(log_path, full_cmd, result, fallback_cmd, fallback_result)
        result = fallback_result
    else:
        write_pymapconv_log(log_path, full_cmd, result)

    combined_output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if combined_output:
        status(94, f"PyMapConv output written to {log_path}\n{combined_output[-1600:]}")
    if pymapconv_source_cli_succeeded(result, output_smf, combined_output):
        result = subprocess.CompletedProcess(result.args, 0, result.stdout, result.stderr)

    if result.returncode != 0:
        details = combined_output[-2200:] or "No stdout/stderr was produced."
        raise RuntimeError(f"PyMapConv failed with exit code {result.returncode}. Full log: {log_path}\n{details}")

    smf_path = find_file(compiled_maps, ".smf") or output_smf
    smt_path = find_file(compiled_maps, ".smt")
    if not smf_path.exists():
        raise RuntimeError("PyMapConv finished, but no .smf file was produced.")
    if smt_path is None:
        smt_path = find_file(root, ".smt")
    if smt_path is None:
        raise RuntimeError("PyMapConv finished, but no .smt file was produced.")

    status(97, "Packing Spring/BAR .sdz container...")
    if map_container.exists():
        shutil.rmtree(map_container)
    map_container_maps.mkdir(parents=True)
    shutil.copy2(root / "mapinfo.lua", map_container / "mapinfo.lua")
    shutil.copytree(root / "maphelper", map_container / "maphelper")
    shutil.copy2(smf_path, map_container_maps / f"{config.map_name}.smf")
    shutil.copy2(smt_path, map_container_maps / f"{config.map_name}.smt")
    for suffix in (".png", ".jpg"):
        preview = compiled_maps / f"{config.map_name}{suffix}"
        if preview.exists():
            shutil.copy2(preview, map_container_maps / preview.name)
    source_minimap = root / "assets" / "minimap.png"
    if source_minimap.exists():
        shutil.copy2(source_minimap, map_container / "minimap.png")

    if final_sdz.exists():
        final_sdz.unlink()
    with zipfile.ZipFile(final_sdz, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in map_container.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(map_container).as_posix())

    if final_sdz.stat().st_size <= 0:
        raise RuntimeError(".sdz package was created but is empty.")
    return final_sdz


def ensure_pymapconv(tools_dir: Path, status) -> Path:
    existing = tools_dir / "pymapconv-source"
    if existing.exists():
        existing.chmod(existing.stat().st_mode | 0o755)
        return existing

    status(91, "Downloading PyMapConv source runner...")
    source_dir = tools_dir / "pymapconv_source"
    source_dir.mkdir(parents=True, exist_ok=True)
    download_text(PYMAPCONV_SOURCE_URL, source_dir / "pymapconv.py")
    download_text(PYMAPCONV_VERSION_URL, source_dir / "version.py")
    (source_dir / "png.py").write_text(
        """class Reader:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("PNG heightmaps are not supported by the embedded PyMapConv runner.")

class Writer:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("PNG writing is not supported by the embedded PyMapConv runner.")
""",
        encoding="utf-8",
    )
    python = shutil.which("python3") or sys.executable
    existing.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
exec "{python}" "{source_dir / 'pymapconv.py'}" "$@"
""",
        encoding="utf-8",
    )
    existing.chmod(0o755)
    return existing


def download_text(url: str, path: Path) -> None:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_text(response.text, encoding="utf-8")


def prepare_pymapconv_runtime(root: Path, tools_dir: Path) -> None:
    temp_dir = root / "temp"
    temp_dir.mkdir(exist_ok=True)
    write_compressonator_wrapper(tools_dir)

    resources_dir = root / "resources"
    resources_dir.mkdir(exist_ok=True)
    geovent = resources_dir / "geovent.bmp"
    if not geovent.exists():
        Image.new("RGB", (64, 64), (128, 128, 128)).save(geovent)


def write_compressonator_wrapper(tools_dir: Path) -> None:
    tools_dir.mkdir(parents=True, exist_ok=True)
    wrapper = tools_dir / "CompressonatorCLI"
    wrapper.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "CompressonatorCLI wrapper expected input and output paths" >&2
  exit 2
fi
input="${@: -2:1}"
output="${@: -1}"
if command -v magick >/dev/null 2>&1; then
  magick "$input" -flip -define dds:compression=dxt1 -define dds:fast-mipmaps=false "$output"
elif command -v convert >/dev/null 2>&1; then
  convert "$input" -flip -define dds:compression=dxt1 -define dds:fast-mipmaps=false "$output"
else
  echo "ImageMagick magick/convert is required for DDS compression" >&2
  exit 127
fi
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)


def run_pymapconv_command(root: Path, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{root / 'tools'}:{env.get('PATH', '')}"
    # The PyInstaller build can leak bundled libraries into child shell calls on
    # NixOS, which breaks `/bin/sh` before ImageMagick can create DDS files.
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=1800, env=env)


def pymapconv_source_cli_succeeded(result: subprocess.CompletedProcess[str], output_smf: Path, output: str) -> bool:
    return (
        result.returncode != 0
        and output_smf.exists()
        and output_smf.with_suffix(".smt").exists()
        and "All Done" in output
    )


def is_texture_compression_failure(output: str) -> bool:
    patterns = (
        "temp/thread",
        "nvdxt.exe",
        "CompressonatorCLI",
        "rl_completion_rewrite_hook",
        "FileNotFoundError",
    )
    return any(pattern in output for pattern in patterns)


def write_pymapconv_log(
    log_path: Path,
    cmd: list[str],
    result: subprocess.CompletedProcess[str],
    fallback_cmd: list[str] | None = None,
    fallback_result: subprocess.CompletedProcess[str] | None = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sections = [
        "BAR Native Map Generator - PyMapConv log",
        f"Command: {' '.join(cmd)}",
        f"Exit code: {result.returncode}",
        "",
        "STDOUT:",
        result.stdout or "",
        "",
        "STDERR:",
        result.stderr or "",
        "",
    ]
    if fallback_cmd and fallback_result:
        sections.extend(
            [
                "",
                "Fallback PyMapConv run",
                f"Command: {' '.join(fallback_cmd)}",
                f"Exit code: {fallback_result.returncode}",
                "",
                "STDOUT:",
                fallback_result.stdout or "",
                "",
                "STDERR:",
                fallback_result.stderr or "",
                "",
            ]
        )
    log_path.write_text("\n".join(sections), encoding="utf-8")


def find_file(root: Path, suffix: str) -> Path | None:
    for path in root.rglob(f"*{suffix}"):
        if path.is_file():
            return path
    return None


def main() -> None:
    root = tk.Tk()
    NativeExporterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
