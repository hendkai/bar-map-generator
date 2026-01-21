# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **single-file web application** (`bar_map_generator.html`) that procedurally generates complete maps for Beyond All Reason (BAR), a Spring-based RTS game. The entire application—HTML, CSS, and JavaScript—is contained in one file with no build step required.

**Key Architecture Pattern**: The application is monolithic—all functionality lives in `bar_map_generator.html`. When making changes, always edit this file directly.

## Development Workflow

### Running the Application
```bash
# Simply open in a browser - no build process required
xdg-open bar_map_generator.html  # Linux
open bar_map_generator.html      # macOS
# Or double-click on Windows
```

### Testing Changes
1. Edit `bar_map_generator.html`
2. Reload browser to see changes
3. No compilation, bundling, or server needed

## Code Architecture

### Core Functions by Responsibility

**Map Generation Pipeline:**
- `generateMap()` - Entry point, orchestrates generation
- `generateHeightmap()` - Creates terrain elevation using noise
- `generateContinentalTerrain()`, `generateIslandTerrain()`, etc. - Terrain algorithms
- `noise2D()` - Simple noise implementation

**BAR Asset Generation** (all called via `generateBARAssets()`):
- `generateBARHeightmap()` - 16-bit PNG: `(64 * mapUnits + 1)`²
- `generateBARMetalmap()` - 8-bit BMP: `(32 * mapUnits)`²
- `generateBARTexture()` - 8-bit BMP: `(512 * mapUnits)`²
- `generateBARNormalmap()` - `(512 * mapUnits)`²
- `generateBARSpecularmap()` - `(256 * mapUnits)`²
- `generateBARMinimap()` - 1024×1024
- `generateBARGrassmap()` - 8-bit BMP: `(16 * mapUnits)`²
- `generateBARTypemap()` - 8-bit BMP: `(32 * mapUnits)`²
- `generateBARSplatmap()` - `(32 * mapUnits)`²

**Build Script Generation:**
- `generatePythonBuildScript()` - Creates `build_map.py` (~900 lines embedded)
- `generateBatchScript()` - Windows wrapper
- `generateBashScript()` - Linux/macOS wrapper

### Map Units System

BAR uses "map units" for asset sizing:
- Small (512×512) = 8×8 units
- Medium (1024×1024) = 16×16 units
- Large (2048×2048) = 32×32 units

Asset dimensions are calculated as: `size / 64 = mapUnits`

**Critical for PyMapConv compatibility**: Each asset type uses a specific multiplier of mapUnits. Changing these formulas will break compilation.

## Important Constraints

1. **Asset Dimensions Must Match PyMapConv Expectations**
   - Heightmap: `64 * mapUnits + 1` (e.g., 1025×1025 for 16×16)
   - Metalmap: `32 * mapUnits` (e.g., 512×512)
   - Texture: `512 * mapUnits` (e.g., 8192×8192)
   - Grassmap: `16 * mapUnits` (e.g., 256×256)

2. **File Formats Matter**
   - Heightmap: 16-bit grayscale PNG
   - Metalmap/Grassmap/Typemap/Texture: 8-bit BMP
   - Others: PNG

3. **Build Scripts are Embedded**
   - The Python build script is generated as a string in `generatePythonBuildScript()`
   - When modifying build logic, edit the template string, not an external file

4. **Single External Dependency**
   - JSZip v3.10.1 loaded from CDN
   - No other external libraries

## Known Issues

- PyMapConv integration is experimental and may fail on some systems
- Linux requires ImageMagick and CompressonatorCLI for full functionality
- Build scripts handle virtual environment setup automatically
- Threading issues with PyMapConv on some configurations

## When Adding Features

1. **New Terrain Types**: Add function following pattern `generate*Terrain()`, update `generateHeightmap()` switch statement
2. **New Asset Types**: Create `generateBAR*()` function, add to `generateBARAssets()`, update asset dimensions formula
3. **New Export Options**: Add button in HTML, create download function, call from `downloadCompleteMapPackage()`

## Code Organization in bar_map_generator.html

- Lines 1-150: CSS styles
- Lines 152-276: HTML structure (UI controls, canvas elements)
- Lines 277-end: JavaScript (all functions)
