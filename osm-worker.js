importScripts('map-worker.js');

self.onmessage = async function (event) {
    const { bounds, featureMask, elevationGrid, config } = event.data;

    try {
        const generated = await buildTerrainFromOsmWorker(bounds, featureMask, elevationGrid, config);
        self.postMessage({
            type: 'complete',
            heightmap: generated.heightmap,
            texture: generated.texture,
            resources: generated.resources,
            config: generated.config,
            elevationMetadata: generated.elevationMetadata
        }, [generated.heightmap.buffer, generated.texture.buffer]);
    } catch (error) {
        self.postMessage({ type: 'error', message: error.message });
    }
};

async function buildTerrainFromOsmWorker(bounds, featureMask, elevationGrid, config) {
    const { size, playerCount, heightScale, metalSpots, metalStrength, geoSpots, seed } = config;
    const waterLevel = 58;
    const heightmap = new Float32Array(size * size);
    const texture = new Uint8ClampedArray(size * size * 4);
    const rowYieldStep = size >= 2048 ? 32 : 64;

    postProgress(79, 'Rasterizing OSM landscape features...');

    const elevationMetadata = normalizeElevationMetadata(elevationGrid);
    const finiteElevationValues = elevationGrid.values.filter(Number.isFinite);
    const minElevation = Number.isFinite(elevationMetadata.minElevationMeters)
        ? elevationMetadata.minElevationMeters
        : Math.min(...finiteElevationValues);
    const maxElevation = Number.isFinite(elevationMetadata.maxElevationMeters)
        ? elevationMetadata.maxElevationMeters
        : Math.max(...finiteElevationValues);
    const elevationRange = Math.max(1, maxElevation - minElevation);

    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const mask = sampleFeatureMask(featureMask, u, v);
            const elevation = sampleElevation(elevationGrid, u, v);
            const normalizedElevation = (elevation - minElevation) / elevationRange;
            const localNoise = (noise2D(x * 0.018, y * 0.018) * 7) + (noise2D(x * 0.055, y * 0.055) * 2);
            let height = 72 + normalizedElevation * 150 * heightScale + localNoise;

            if (mask.water > 0) height = Math.min(height, waterLevel - 14 - mask.water * 12);
            if (mask.road > 0) height = height * 0.92 + 78 * 0.08;
            if (mask.urban > 0) height = height * 0.86 + 82 * 0.14;
            if (mask.rock > 0) height += 18 * mask.rock;

            heightmap[y * size + x] = Math.max(0, Math.min(255, height));
        }
        if (y % rowYieldStep === 0 || y === size - 1) {
            postProgress(80 + (y / (size - 1)) * 7, `Building heightmap row ${y + 1}/${size}...`);
        }
    }

    for (let i = 0; i < 2; i++) {
        postProgress(88 + i, `Smoothing terrain pass ${i + 1}/2...`);
        smoothHeightmap(heightmap, size);
    }

    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const i = y * size + x;
            const mask = sampleFeatureMask(featureMask, u, v);
            const height = heightmap[i];
            const pixel = i * 4;
            const slope = estimateLocalSlope(heightmap, size, x, y);
            const color = getOsmTerrainColor(mask, height, waterLevel, slope);

            texture[pixel] = color[0];
            texture[pixel + 1] = color[1];
            texture[pixel + 2] = color[2];
            texture[pixel + 3] = 255;
        }
        if (y % rowYieldStep === 0 || y === size - 1) {
            postProgress(90 + (y / (size - 1)) * 4, `Painting texture row ${y + 1}/${size}...`);
        }
    }

    postProgress(95, 'Finding start positions...');
    currentTerrainType = 'continental';
    const startPositions = generateStartPositions(size, playerCount, heightmap, waterLevel, 'continental', seed);

    postProgress(96, 'Analyzing terrain for resources...');
    const terrainAnalysis = analyzeTerrain(heightmap, size, waterLevel);

    postProgress(97, 'Placing metal and geothermal spots...');
    const resources = generateResourceMap(
        size,
        heightmap,
        waterLevel,
        metalSpots,
        geoSpots,
        playerCount,
        metalStrength,
        terrainAnalysis,
        seed
    );

    return {
        heightmap,
        texture,
        resources,
        config: {
            size,
            terrainType: 'osm',
            playerCount,
            noiseStrength: 0,
            heightVariation: 180,
            waterLevel,
            metalSpots,
            metalStrength,
            geoSpots,
            startPositions,
            osmBounds: bounds,
            elevationMetadata
        },
        elevationMetadata
    };
}

function normalizeElevationMetadata(elevationGrid) {
    const gridWidth = elevationGrid.gridWidth || elevationGrid.gridSize || Math.sqrt(elevationGrid.values.length);
    const gridHeight = elevationGrid.gridHeight || elevationGrid.gridSize || gridWidth;
    const values = elevationGrid.values || [];
    const finiteValues = values.filter(Number.isFinite);
    const fallbackMetadata = {
        source: elevationGrid.synthetic ? 'synthetic-fallback' : 'unknown',
        providerName: elevationGrid.synthetic ? 'Procedural synthetic relief' : 'Legacy elevation grid',
        gridWidth,
        gridHeight,
        sampleCount: finiteValues.length,
        minElevationMeters: finiteValues.length ? Math.min(...finiteValues) : 0,
        maxElevationMeters: finiteValues.length ? Math.max(...finiteValues) : 0,
        synthetic: Boolean(elevationGrid.synthetic),
        fallbackReason: elevationGrid.synthetic ? 'Legacy synthetic elevation grid' : null
    };
    return Object.assign(fallbackMetadata, elevationGrid.metadata || {});
}

function postProgress(percent, message) {
    self.postMessage({ type: 'progress', percent, message });
}

function noise2D(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
    return (n - Math.floor(n)) * 2 - 1;
}

function sampleFeatureMask(mask, u, v) {
    const x = Math.max(0, Math.min(mask.width - 1, Math.floor(u * (mask.width - 1))));
    const y = Math.max(0, Math.min(mask.height - 1, Math.floor(v * (mask.height - 1))));
    const i = (y * mask.width + x) * 4;
    const d = mask.data;
    const r = d[i];
    const g = d[i + 1];
    const b = d[i + 2];

    return {
        rock: r > 200 && g < 80 && b < 80 ? 1 : 0,
        forest: g > 180 && r < 80 && b < 80 ? 1 : 0,
        water: b > 180 && r < 80 && g < 80 ? 1 : 0,
        road: g > 180 && b > 180 && r < 80 ? 1 : 0,
        sand: r > 180 && b > 180 && g < 80 ? 1 : 0,
        field: r > 180 && g > 180 && b < 80 ? 1 : 0,
        urban: r > 180 && g > 80 && g < 180 && b < 80 ? 1 : 0
    };
}

function sampleElevation(grid, u, v) {
    const gridWidth = grid.gridWidth || grid.gridSize || Math.sqrt(grid.values.length);
    const gridHeight = grid.gridHeight || grid.gridSize || gridWidth;
    const maxX = gridWidth - 1;
    const maxY = gridHeight - 1;
    const gx = u * maxX;
    const gy = v * maxY;
    const x0 = Math.floor(gx);
    const y0 = Math.floor(gy);
    const x1 = Math.min(maxX, x0 + 1);
    const y1 = Math.min(maxY, y0 + 1);
    const tx = gx - x0;
    const ty = gy - y0;
    const at = (x, y) => grid.values[y * gridWidth + x] || 0;
    const a = at(x0, y0) * (1 - tx) + at(x1, y0) * tx;
    const b = at(x0, y1) * (1 - tx) + at(x1, y1) * tx;
    return a * (1 - ty) + b * ty;
}

function estimateLocalSlope(data, size, x, y) {
    const left = data[y * size + Math.max(0, x - 1)];
    const right = data[y * size + Math.min(size - 1, x + 1)];
    const top = data[Math.max(0, y - 1) * size + x];
    const bottom = data[Math.min(size - 1, y + 1) * size + x];
    return Math.sqrt((right - left) ** 2 + (bottom - top) ** 2);
}

function getOsmTerrainColor(mask, height, waterLevel, slope) {
    if (height < waterLevel || mask.water > 0.1) return [26, 92, 143];
    if (mask.sand > 0.1 || height < waterLevel + 8) return [194, 178, 125];
    if (mask.road > 0.1) return [102, 101, 94];
    if (mask.urban > 0.1) return [112, 104, 96];
    if (mask.rock > 0.1 || slope > 18) return [117, 113, 105];
    if (mask.forest > 0.1) return [50, 105, 64];
    if (mask.field > 0.1) return [128, 139, 78];
    if (height > waterLevel + 115) return [138, 139, 132];
    return [74, 134, 82];
}
