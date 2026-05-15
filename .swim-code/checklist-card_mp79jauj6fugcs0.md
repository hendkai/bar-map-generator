# Card: Fix horizontal banding in generated map textures

## Acceptance Criteria

## ⚠ Planner-File-Tree Mismatch (auto-detected)

The plan above references file paths that do NOT exist in this repository, and were not marked as "new" / "create":

- asset/export
- heightmap/texture/resources
- alternate/root
- .auto-claude/specs/
- BAR/PyMapConv-specific
- metalmap/typemap
- preview/generation
- assets/texture.bmp
- padding/stride
- Native/build
- native/PyMapConv
- elevation/export
- … (9 more)

Before acting on those paths: verify each with list_directory / ls / find. The planner may have hallucinated a layout. If a referenced file actually lives at a different path, use that path; if it's a genuinely-new file the plan didn't flag as such, create it under a directory that already exists — don't mkdir a directory the planner mentioned but the repo doesn't have.

---

## Codebase Analysis

### Project Structure

Root entry points from the provided tree:

- `bar_map_generator.html`: main single-file browser app and BAR asset/export generator.
- `map-worker.js`: procedural map worker; creates heightmap, texture, resources.
- `osm-worker.js`: OSM terrain worker; creates OSM heightmap/texture/resources off the UI thread.
- `desktop_native.py`: native desktop exporter; writes assets, invokes PyMapConv, packages `.sdz`.
- `desktop-main.cjs`: Electron shell entry.
- `index.html`: alternate/root web entry.
- `frontend/`: community portal UI.
- `backend/`: FastAPI-style backend for auth, maps, ratings, storage.
- `tests/`: manual and Node harness tests, including `tests/elevation-pipeline-harness.js`.
- `.auto-claude/specs/`: implementation notes for earlier validation and 3D preview work.

No `package.json` is present in the listed tree, so there is no Node build script or package-managed frontend workflow.

### Conventions & Patterns

The generator is mostly monolithic: project guidance says changes should normally happen directly in `bar_map_generator.html`. Asset dimensions are BAR/PyMapConv-specific and must stay formula-based:

- texture: `512 * mapUnits`
- heightmap: `64 * mapUnits + 1`
- metalmap/typemap: `32 * mapUnits`
- grassmap: `16 * mapUnits`

Texture data is represented as flat row-major RGBA arrays: index math consistently follows `(y * size + x) * 4`.

Browser export uses `JSZip`, canvas blobs, and an embedded generated Python build script. Native export uses Pillow and writes image files directly before running PyMapConv.

### Relevant Code

The preview/generation side looks internally coherent:

- [osm-worker.js](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/osm-worker.js:23) creates `Uint8ClampedArray(size * size * 4)` and fills pixels row-major.
- [map-worker.js](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/map-worker.js:414) creates procedural `textureData` with `idx = i * 4`.
- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:2506) draws previews by sampling `sourceIndex = (sourceY * size + sourceX) * 4`.
- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:6012) builds the BAR texture canvas by scaling a correctly assembled source canvas.

The most suspicious corruption point is browser package export:

- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:6340) exports textures as PNG for maps larger than 512.
- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:6352) stores those PNG bytes under `assets/texture.bmp`.
- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:4248) generated `fix_asset_formats()` only re-saves `texture.bmp` as BMP when Pillow opens it as `RGBA`/`LA`. If Pillow opens the PNG as `RGB`, the file remains PNG content with a `.bmp` name.
- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:4680) then passes `assets/texture.bmp` to PyMapConv as a BMP texture.

The custom BMP writer itself appears structurally correct:

- [bar_map_generator.html](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/bar_map_generator.html:6450) writes 24-bit BMP, computes row padding/stride, and writes rows bottom-up. For BAR texture sizes like `4096`, `8192`, `16384`, `w * 3` is already 4-byte aligned.

Native export has a cleaner texture path:

- [desktop_native.py](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/desktop_native.py:1144) resizes a Pillow RGB texture and saves `texture.bmp` directly.
- [desktop_native.py](/home/hendrik/bar-map-generator/.worktrees/card_mp79jauj6fugcs0/desktop_native.py:1406) generates `base_texture` as a Pillow RGB image row-by-row.

### Dependencies

Relevant external dependencies:

- Browser:
  - JSZip CDN for package creation.
  - Browser Canvas APIs: `createImageData`, `putImageData`, `drawImage`, `toBlob`.
  - Web Workers: `map-worker.js`, `osm-worker.js`.

- Native/build:
  - Python generated by `generatePythonBuildScript()`.
  - Pillow for image format conversion.
  - PyMapConv / Spring map compiler.
  - ImageMagick / Compressonator may be involved downstream for texture compression in native/PyMapConv flows.
  - `desktop_native.py` uses `PIL`, `requests`, and `tkinter`.

### Current State

The likely bug is not in worker row indexing or preview canvas assembly. The row-major texture arrays and preview downsampling are consistent across procedural and OSM flows.

The higher-risk browser export path can produce a file named `texture.bmp` that actually contains PNG bytes for maps larger than `512`. The generated Python build script tries to fix this, but only conditionally re-saves when the opened image has alpha. A robust fix should make `fix_asset_formats()` always normalize `assets/texture.bmp` to actual RGB BMP, regardless of Pillow mode, and likely avoid storing PNG bytes under a `.bmp` name in the first place.

I verified the existing Node harness with:

```bash
node tests/elevation-pipeline-harness.js
```

It passed. This covers elevation/export helper behavior, but it does not currently validate texture file headers, decoded dimensions, row continuity, or final PyMapConv texture output, so the banding regression is not covered by automated tests.

---

## Architecture Design

### Architecture Overview
Fix this at the export boundary, not in terrain generation. The provided analysis shows worker texture arrays, preview sampling, and native export are already row-major and coherent. The browser package path is the likely corruption source because large textures can be encoded as PNG bytes but stored as `assets/texture.bmp`, then passed to PyMapConv as if it were a BMP.

The technical solution should make texture format normalization explicit and verifiable:

1. Browser export should write `assets/texture.bmp` as real BMP bytes for all map sizes, or store PNG as `.png` and convert before PyMapConv.
2. The generated Python build script should always normalize `assets/texture.bmp` to RGB BMP, regardless of Pillow mode.
3. Add validation that checks image headers, dimensions, decoded size, and row continuity before PyMapConv runs.
4. Add a focused test path that reproduces the large-texture export path and verifies `texture.bmp` is actually BMP.

### Task Breakdown
1. Add texture export diagnostics around browser package generation — `bar_map_generator.html`
2. Replace size-based PNG fallback for large textures with a format-correct path — `bar_map_generator.html`
3. Harden `fix_asset_formats()` so `assets/texture.bmp` is always rewritten as RGB BMP — `bar_map_generator.html`
4. Add pre-PyMapConv texture validation in the generated build script — `bar_map_generator.html`
5. Add equivalent validation or reuse logic in native export if needed — `desktop_native.py`
6. Add regression coverage for texture headers, dimensions, and row layout — `tests/texture-export-harness.js`
7. Manually verify procedural and OSM exports at 512, 1024, and 2048 source sizes — browser/native package flow

### File Changes
| File | Action | Description |
|------|--------|-------------|
| `bar_map_generator.html` | modify | Fix browser BAR texture export so `assets/texture.bmp` contains real BMP bytes, not PNG bytes with a BMP extension. |
| `bar_map_generator.html` | modify | Update generated `fix_asset_formats()` to always open, convert to RGB, and save `texture.bmp` as BMP. Do not make conversion conditional on alpha modes only. |
| `bar_map_generator.html` | modify | Add generated Python validation before PyMapConv: assert BMP signature, expected dimensions, RGB mode after decode, and no obvious repeated chunk rows. |
| `desktop_native.py` | inspect/possibly modify | Native path already saves RGB BMP directly, but add matching validation if final packaged textures can still be corrupted downstream. |
| `tests/texture-export-harness.js` | create | Node/browser-compatible regression harness for BMP header, stride, dimensions, and sampled row continuity. |
| `tests/elevation-pipeline-harness.js` | modify optional | Keep existing elevation coverage separate unless shared helpers are useful. |

### Data Models
```typescript
type TextureExportFormat = 'bmp' | 'png';

interface TextureExportSpec {
  assetName: 'texture';
  mapUnits: number;
  expectedWidth: number;   // 512 * mapUnits
  expectedHeight: number;  // 512 * mapUnits
  outputPath: 'assets/texture.bmp';
  format: 'bmp';
  channels: 3;
}

interface ImageValidationResult {
  path: string;
  exists: boolean;
  detectedFormat: string;
  width: number;
  height: number;
  mode: string;
  expectedWidth: number;
  expectedHeight: number;
  valid: boolean;
  errors: string[];
}

interface BmpHeaderInfo {
  signature: 'BM';
  fileSize: number;
  pixelOffset: number;
  dibHeaderSize: number;
  width: number;
  height: number;
  bitsPerPixel: 24 | 32 | number;
  rowStride: number;
  topDown: boolean;
}
```

### Integration Points
`generateBARTexture()` remains the single browser texture assembly point. It should still create the high-resolution texture canvas from the source texture data, but its export helper must produce actual BMP bytes when the destination filename is `texture.bmp`.

`downloadCompleteMapPackage()` or the local asset packaging function should call one explicit helper, for example `canvasToBmpBlob(textureCanvas)`, instead of switching to PNG for large maps.

`generatePythonBuildScript()` should treat browser-provided assets as untrusted input. Its `fix_asset_formats()` should always normalize `assets/texture.bmp` like this conceptually: open with Pillow, convert to RGB, save to a temporary BMP, replace the original file, then validate header and dimensions.

PyMapConv integration should only receive a verified BMP texture path. If validation fails, the build script should stop with a clear error before PyMapConv produces broken `.smt` chunks.

The native exporter can keep its current Pillow RGB BMP save path, but sharing the same validation logic reduces future drift between browser and native exports.

### Testing Guidance
Test the bug at the exact boundary where it likely appears: the packaged source assets before PyMapConv, not only the preview canvas.

Suggested checks:

1. Generate a large map package from the browser path.
2. Extract `assets/texture.bmp`.
3. Verify first bytes are `BM`, not PNG magic bytes.
4. Verify dimensions are exactly `512 * mapUnits`.
5. Decode with Pillow or a JS BMP parser and sample rows across chunk boundaries.
6. Compare sampled colors from top, middle, and bottom rows against the source canvas/downsampled preview to catch repeated horizontal bands.
7. Run the same checks for OSM and procedural generation.
8. Run final PyMapConv build and inspect the generated map in BAR for continuous terrain texture.

Keep `node tests/elevation-pipeline-harness.js` as a baseline, but add a dedicated texture harness because the current test does not cover image headers, stride, or exported texture continuity.

---

## Risk & Acceptance Criteria

### Acceptance Criteria
- [ ] AC-1: Browser BAR package export always writes `assets/texture.bmp` with a valid BMP `BM` header for every supported map size, including sizes larger than 512.
- [ ] AC-2: Exported texture dimensions are exactly `512 * mapUnits` wide and `512 * mapUnits` high for 8x8, 16x16, and 32x32 BAR maps.
- [ ] AC-3: The generated Python build script always normalizes `assets/texture.bmp` to RGB BMP before invoking PyMapConv, regardless of the image mode Pillow detects.
- [ ] AC-4: The build script fails before PyMapConv with a clear error if `assets/texture.bmp` is missing, not BMP, has wrong dimensions, or cannot be decoded.
- [ ] AC-5: Large procedural map exports produce a continuous texture with no repeated horizontal bands, stacked chunks, or broken row offsets when decoded from the packaged asset.
- [ ] AC-6: Large OSM map exports produce a continuous texture with no repeated horizontal bands, stacked chunks, or broken row offsets when decoded from the packaged asset.
- [ ] AC-7: Regression coverage verifies BMP signature, dimensions, row stride, and sampled row continuity for exported `texture.bmp`.
- [ ] AC-8: Existing elevation pipeline tests still pass after the texture export changes.
- [ ] AC-9: Native export either remains verified as already writing valid RGB BMP textures or gains equivalent validation without changing its existing successful output format.
- [ ] AC-10: No BAR/PyMapConv asset dimension formulas are changed for heightmap, texture, metalmap, typemap, or grassmap.

### Audit Surfaces
- `browser-texture-export`: `bar_map_generator.html` texture canvas export and package asset creation.
- `bmp-writer-stride`: Custom BMP writer header, row padding, bottom-up row order, and byte offsets.
- `build-script-normalization`: Generated `fix_asset_formats()` behavior for `assets/texture.bmp`.
- `pre-pymapconv-validation`: Generated build script checks before PyMapConv invocation.
- `native-texture-export`: `desktop_native.py` Pillow texture save and optional validation path.
- `texture-regression-harness`: Dedicated tests for BMP headers, dimensions, stride, and row continuity.
- `bar-asset-dimensions`: BAR/PyMapConv size formulas and mapUnits calculations.

### Edge Cases
Highest risk is large texture export memory pressure. A 32x32 map texture is 16384x16384, so the fix must avoid browser crashes while still producing a real BMP.

Check row boundaries around likely chunk seams: top row, bottom row, midpoint, every 512 or 1024 pixels vertically, and near BMP bottom-up inversion boundaries.

Validate both square procedural maps and OSM-derived textures because the source texture may come from different workers even if final export is shared.

Handle canvases whose `toBlob()` fails or returns null with a clear export error instead of silently packaging corrupt assets.

### Security Considerations
Generated Python validation should treat packaged assets as untrusted local input: open with Pillow safely, validate dimensions before processing, and fail closed on decode errors.

Avoid introducing network fetches, dynamic code execution, shell interpolation, or path traversal in generated build-script changes.

Error messages should report asset path and validation failure without dumping large binary data or user-local sensitive paths beyond the build directory context.

### Performance Risks
Full-size BMP generation for 8192 or 16384 textures can consume substantial memory and time in the browser. The implementation should be careful about duplicate full-image buffers.

Row-continuity validation should use sampled rows, not exhaustive pixel comparisons across the whole texture, unless done in a controlled test harness.

Repeated Pillow open/save cycles in the build script should be limited to required normalization and validation to avoid slowing normal exports too much.

### Testing Strategy
Add `tests/texture-export-harness.js` focused on the export boundary. It should verify BMP magic bytes, DIB width/height, bits-per-pixel, computed row stride, pixel offset, and sampled row continuity.

Run existing baseline:

```bash
node tests/elevation-pipeline-harness.js
```

Add manual verification for procedural and OSM exports at 512, 1024, and 2048 source sizes. Extract `assets/texture.bmp`, confirm it decodes as BMP, then inspect representative rows and final BAR output.

For the generated Python build script, test failure cases: PNG bytes renamed to `.bmp`, wrong dimensions, missing texture file, and valid RGB BMP.

### Backward Compatibility
Do not change BAR asset naming, package layout, or PyMapConv dimension formulas.

Existing packages should still contain `assets/texture.bmp`; the change is that the bytes must now always match the extension.

Native export should continue producing valid `.sdz` packages named after the map and should not regress minimap or preview asset packaging.

## Forbidden patterns (auto-extracted)

Lines in your diff matching these patterns will mechanically fail the audit
regardless of what the auditor model says. Do not ship code containing these.

_(none parsed from ACs)_

## How this file is used

Read this file at the start of your run to anchor on the goal, and again
before calling task_done so you can verify each AC. The verification gate
will require you to cite a file:line of evidence for each AC.
