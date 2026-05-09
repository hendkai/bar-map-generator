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
import tarfile
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from tkinter import END, filedialog, messagebox, ttk
import tkinter as tk

import requests
from PIL import Image, ImageDraw, ImageFilter


OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
PYMAPCONV_LINUX_URL = "https://github.com/Beherith/springrts_smf_compiler/releases/download/v0.6.3/pymapconv.v0.6.3.linux-amd64.tar.gz"


class NativeExporterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BAR Map Generator - Native Desktop Exporter")
        self.root.geometry("920x720")
        self.root.minsize(820, 620)
        self.worker: threading.Thread | None = None

        self.map_name = tk.StringVar(value="native_osm_map")
        self.location = tk.StringVar(value="Berlin")
        self.map_size = tk.StringVar(value="1024")
        self.players = tk.StringVar(value="4")
        self.area_km = tk.StringVar(value="4.0")
        self.height_scale = tk.StringVar(value="1.0")
        self.output_path = tk.StringVar(value=str(Path.home() / "BAR_native_map.sd7"))
        self.status = tk.StringVar(value="Ready.")
        self.progress = tk.DoubleVar(value=0)

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
        style.configure("TEntry", fieldbackground="#131b24", foreground="#e8f4ff", insertcolor="#e8f4ff")
        style.configure("TCombobox", fieldbackground="#131b24", foreground="#e8f4ff")
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
            ttk.Combobox(grid, textvariable=self.map_size, values=("512", "1024", "2048"), state="readonly"),
        )
        row += 1
        self._row(
            grid,
            row,
            "Players",
            ttk.Combobox(grid, textvariable=self.players, values=("2", "4", "6", "8"), state="readonly"),
        )
        row += 1
        self._row(
            grid,
            row,
            "Height scale",
            ttk.Combobox(grid, textvariable=self.height_scale, values=("0.7", "1.0", "1.35"), state="readonly"),
        )
        row += 1

        output_frame = ttk.Frame(grid)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_path).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(output_frame, text="Browse", command=self._choose_output).grid(row=0, column=1)
        self._row(grid, row, "Output .sd7", output_frame)

        note = ttk.Label(
            shell,
            text=(
                "This native exporter generates the source assets, runs PyMapConv, and packages a BAR-loadable .sd7. "
                "2048 maps can take several minutes and use several GB of temporary disk space."
            ),
            style="Sub.TLabel",
            wraplength=820,
        )
        note.pack(fill="x", pady=(18, 10))

        ttk.Progressbar(shell, variable=self.progress, maximum=100).pack(fill="x", pady=(0, 8))
        ttk.Label(shell, textvariable=self.status).pack(anchor="w", pady=(0, 14))

        actions = ttk.Frame(shell)
        actions.pack(fill="x")
        ttk.Button(actions, text="Generate Playable .sd7", style="Accent.TButton", command=self._start_export).pack(side="left")
        ttk.Button(actions, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=10)

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
            defaultextension=".sd7",
            filetypes=(("BAR map", "*.sd7"), ("All files", "*.*")),
            initialfile=Path(self.output_path.get()).name,
        )
        if filename:
            self.output_path.set(filename)

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
                area_km=float(self.area_km.get()),
                height_scale=float(self.height_scale.get()),
                output=Path(self.output_path.get()).expanduser(),
            )
            export_native_package(config, self._set_status)
            self._set_status(100, f"Done: {config.output}")
            self.root.after(0, messagebox.showinfo, "Export complete", f"Created:\n{config.output}")
        except Exception as exc:
            self._set_status(0, f"Export failed: {exc}")
            self.root.after(0, messagebox.showerror, "Export failed", str(exc))


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
    ) -> None:
        self.map_name = map_name
        self.location = location
        self.size = size
        self.players = players
        self.area_km = area_km
        self.height_scale = height_scale
        self.output = output


def sanitize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "native_osm_map"


def export_native_package(config: ExportConfig, status) -> None:
    if config.output.suffix.lower() != ".sd7":
        config.output = config.output.with_suffix(".sd7")
    map_units = config.size // 64
    bounds = resolve_bounds(config.location, config.area_km, status)

    with tempfile.TemporaryDirectory(prefix="bar-native-export-") as tmp:
        root = Path(tmp)
        assets = root / "assets"
        assets.mkdir()

        status(15, "Sampling elevation grid...")
        elevation = load_elevation_grid(bounds, grid_size=24, status=status)

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

        status(90, "Compiling playable .sd7 with PyMapConv...")
        final_sd7 = compile_playable_sd7(root, config, status)
        shutil.copy2(final_sd7, config.output)


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
            values.extend(float(v or 0) for v in elevations)
            status(15 + 10 * min(1, len(values) / len(points)), f"Elevation samples: {len(values)}/{len(points)}")
            time.sleep(0.1)
    except Exception:
        values = []

    if len(values) != len(points):
        random.seed(int(abs(bounds["lat"] * 1000 + bounds["lon"] * 1000)))
        values = []
        for y in range(grid_size):
            for x in range(grid_size):
                u = x / (grid_size - 1)
                v = y / (grid_size - 1)
                values.append(90 + math.sin((u * 2 + v) * math.pi) * 24 + noise(u * 8, v * 8) * 18)
    return {"grid_size": grid_size, "values": values}


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
    min_el = min(elevation["values"])
    max_el = max(elevation["values"])
    span = max(1, max_el - min_el)
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
            h = 72 + ((elev - min_el) / span) * 150 * config.height_scale + noise(x * 0.025, y * 0.025) * 8
            m = mask.getpixel((x, y))
            if m == (0, 0, 255):
                h = min(h, 42)
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
    if tags.get("waterway") or tags.get("natural") in {"water", "wetland"}:
        return (0, 0, 255)
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
    n = grid["grid_size"] - 1
    gx = u * n
    gy = v * n
    x0 = int(gx)
    y0 = int(gy)
    x1 = min(n, x0 + 1)
    y1 = min(n, y0 + 1)
    tx = gx - x0
    ty = gy - y0

    def at(x, y):
        return grid["values"][y * grid["grid_size"] + x]

    a = at(x0, y0) * (1 - tx) + at(x1, y0) * tx
    b = at(x0, y1) * (1 - tx) + at(x1, y1) * tx
    return a * (1 - ty) + b * ty


def noise(x: float, y: float) -> float:
    n = math.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return (n - math.floor(n)) * 2 - 1


def terrain_color(height: int, mask):
    if height < 58 or mask == (0, 0, 255):
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

The native GUI already attempted to create the final `.sd7`. To rebuild from
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
    output=Path("output/{config.map_name}.sd7"),
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
    final_sd7 = output_dir / f"{config.map_name}.sd7"

    tools_dir.mkdir(exist_ok=True)
    compiled_maps.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pymapconv = ensure_pymapconv(tools_dir, status)

    cmd = [
        str(pymapconv),
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
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=1800)
    if result.stdout.strip():
        status(94, result.stdout.strip()[-900:])
    if result.returncode != 0:
        raise RuntimeError(f"PyMapConv failed:\n{result.stderr[-1800:] or result.stdout[-1800:]}")

    smf_path = find_file(compiled_maps, ".smf") or output_smf
    smt_path = find_file(compiled_maps, ".smt")
    if not smf_path.exists():
        raise RuntimeError("PyMapConv finished, but no .smf file was produced.")
    if smt_path is None:
        smt_path = find_file(root, ".smt")
    if smt_path is None:
        raise RuntimeError("PyMapConv finished, but no .smt file was produced.")

    status(97, "Packing Spring/BAR .sd7 container...")
    if map_container.exists():
        shutil.rmtree(map_container)
    map_container_maps.mkdir(parents=True)
    shutil.copy2(root / "mapinfo.lua", map_container / "mapinfo.lua")
    shutil.copytree(root / "maphelper", map_container / "maphelper")
    shutil.copy2(smf_path, map_container_maps / f"{config.map_name}.smf")
    shutil.copy2(smt_path, map_container_maps / f"{config.map_name}.smt")

    if final_sd7.exists():
        final_sd7.unlink()
    with zipfile.ZipFile(final_sd7, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in map_container.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(map_container).as_posix())

    if final_sd7.stat().st_size <= 0:
        raise RuntimeError(".sd7 package was created but is empty.")
    return final_sd7


def ensure_pymapconv(tools_dir: Path, status) -> Path:
    existing = next(tools_dir.rglob("pymapconv"), None)
    if existing and existing.is_file():
        existing.chmod(existing.stat().st_mode | 0o755)
        return existing

    archive_path = tools_dir / "pymapconv-linux-amd64.tar.gz"
    status(91, "Downloading PyMapConv...")
    with requests.get(PYMAPCONV_LINUX_URL, stream=True, timeout=120) as response:
        response.raise_for_status()
        with archive_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(tools_dir)

    executable = next(tools_dir.rglob("pymapconv"), None)
    if not executable:
        raise RuntimeError("PyMapConv download completed, but executable was not found.")
    executable.chmod(executable.stat().st_mode | 0o755)
    return executable


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
