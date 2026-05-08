# BAR Map Generator

🗺️ **Procedural Map Generator for Beyond All Reason (BAR)**

A web-based tool that generates complete, playable maps for the RTS game Beyond All Reason with automatic compilation and packaging.

## ⚠️ Development Status

**This project is currently in active development and not yet fully functional.**

While the map generation and asset creation works, the automatic compilation system is still being refined. The PyMapConv integration and build scripts are experimental and may not work reliably on all systems.

## 🎯 Features

- **Procedural Terrain Generation**: Multiple terrain types (Continental, Islands, Canyon, Hills, Flat)
- **OSM Terrain Import**: Select a real-world area with OpenStreetMap and derive terrain from landscape, water, roads, land-use, and elevation data
- **OSM Location Search**: Search addresses, cities, or landmarks before drawing a visible red selection rectangle
- **Resource Distribution**: Automatic metal and geothermal spot placement
- **Complete Asset Generation**: All required BAR map assets (heightmap, metalmap, texture, normalmap, etc.)
- **Self-Compiling Packages**: Generates complete build packages with Python scripts
- **Cross-Platform Support**: Windows and Linux build scripts included
- **PyMapConv Integration**: Automatic download and compilation using modern Spring map tools

## 🚀 Quick Start

1. Open `bar_map_generator.html` in your web browser
2. Choose either "Procedural" or "Import from OSM"
3. Adjust map parameters or draw an OSM selection area
4. Click "Generate Map" or "Generate from Selection" to create preview
5. Download complete map package
6. Run the included build script to compile the map

## 📋 Requirements

- **Web Browser**: Modern browser with JavaScript support
- **Python 3.6+**: For map compilation (downloaded automatically)
- **Internet Connection**: For downloading Spring map tools
- **~500MB Free Space**: For tools and temporary files

## 🛠️ How It Works

1. **Generation**: Creates procedural terrain using noise algorithms
   - OSM mode combines OpenStreetMap features with sampled elevation data
   - Elevation samples are loaded in throttled batches with an in-page progress bar to reduce pressure on public APIs
   - If the public elevation API is rate-limited, OSM mode falls back to generated relief so the map can still be previewed and exported
2. **Asset Creation**: Generates all required BAR map files with correct dimensions
3. **Package Creation**: Bundles everything into a self-compiling ZIP package
4. **Compilation**: Uses PyMapConv to create the final .sd7 map file
5. **Installation**: Automatically copies map to your BAR directory

## 📁 Generated Assets

The generator creates all required BAR map assets:

- **Heightmap** (1025×1025): Terrain elevation data
- **Metalmap** (512×512): Metal resource distribution  
- **Texture** (8192×8192): Surface textures
- **Normalmap** (8192×8192): Surface detail normals
- **Specularmap** (4096×4096): Reflection/shininess
- **Minimap** (1024×1024): Overview image
- **Grassmap** (256×256): Vegetation density
- **Typemap** (512×512): Terrain type classification
- **Splatmap** (2048×2048): Detail texture mapping
- **mapinfo.lua**: Map configuration and metadata

## 🔧 Technical Details

### Map Dimensions
- **Small**: 512×512 (8×8 Spring units)
- **Medium**: 1024×1024 (16×16 Spring units) 
- **Large**: 2048×2048 (32×32 Spring units)

### Asset Resolutions
All assets are generated with correct dimensions for PyMapConv compatibility:
- Heightmap: (64 × map_units + 1)²
- Metalmap: (32 × map_units)²
- Grassmap: (16 × map_units)²
- Typemap: (32 × map_units)²
- Texture: (512 × map_units)²

### Compilation Pipeline
1. **PyMapConv Download**: Automatic download of latest release
2. **Asset Validation**: Format and dimension checking
3. **Dependency Installation**: Python packages via virtual environment
4. **Map Compilation**: SMF/SMT generation with error handling
5. **Package Creation**: Final .sd7 archive

## 🐛 Known Issues

- **PyMapConv Integration**: Still experimental, may fail on some systems
- **Linux Dependencies**: ImageMagick and CompressonatorCLI installation needed
- **Temp File Handling**: Threading issues with PyMapConv on some configurations
- **Asset Format Compatibility**: Some format conversions may not work perfectly

## 🆘 Troubleshooting

### "Python not found"
Install Python 3.x from https://python.org and ensure it's in your PATH.

### "PyMapConv download failed"
Check your internet connection or download PyMapConv manually from:
https://github.com/Beherith/springrts_smf_compiler

### "Build failed"
Try running the Python script directly:
```bash
python3 build_map.py
```

### "Map not visible in BAR"
- Restart BAR
- Check if the .sd7 file is in the correct maps/ directory
- Verify file permissions

## 🔮 Planned Features

- **Improved PyMapConv Integration**: More reliable compilation
- **Advanced Terrain Options**: Rivers, cliffs, custom biomes
- **Resource Balancing**: Automatic metal/geo distribution optimization
- **Map Validation**: Pre-compilation testing and validation
- **GUI Improvements**: Better preview system and parameter controls
- **Template System**: Predefined map templates and styles

## 🤝 Contributing

This project is in early development. Contributions are welcome, especially:

- PyMapConv integration improvements
- Cross-platform compatibility fixes
- Asset generation enhancements
- Documentation and testing

## 📄 License

This project is open source. See LICENSE file for details.

## 🔗 Links

- **Beyond All Reason**: https://www.beyondallreason.info/
- **PyMapConv**: https://github.com/Beherith/springrts_smf_compiler
- **Spring Engine**: https://springrts.com/

## 📝 Changelog

### v1.0 (Current)
- Initial release with basic map generation
- PyMapConv integration (experimental)
- Self-compiling package system
- Cross-platform build scripts

---

**Generated with ❤️ for the BAR community**
