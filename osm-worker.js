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
            elevationMetadata: generated.elevationMetadata,
            reliefProfile: generated.reliefProfile,
            topologySignature: generated.topologySignature
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
    const reliefProfile = computeReliefProfile(elevationGrid, { heightScale, waterLevel });

    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const mask = sampleFeatureMask(featureMask, u, v);
            const elevation = sampleElevation(elevationGrid, u, v);
            const normalizedElevation = Math.max(0, Math.min(1, (elevation - reliefProfile.elevationMinMeters) / Math.max(1, reliefProfile.elevationSpanMeters)));
            const localNoise = (noise2D(x * 0.018, y * 0.018) * reliefProfile.detailNoise) + (noise2D(x * 0.055, y * 0.055) * 1.5);
            let height = reliefProfile.heightmapBase + normalizedElevation * reliefProfile.heightmapRange + localNoise;

            if (mask.waterway > 0) {
                height = Math.max(0, height - reliefProfile.waterwayCarveDepth * mask.waterway);
            } else if (mask.water > 0) {
                const waterPlane = reliefProfile.waterLevel - reliefProfile.waterBodyCarveDepth * mask.water;
                height = height * 0.72 + Math.min(height, waterPlane) * 0.28;
            }
            if (mask.road > 0) height = height * 0.96 + (reliefProfile.heightmapBase + 10) * 0.04;
            if (mask.urban > 0) height = height * 0.92 + (reliefProfile.heightmapBase + 12) * 0.08;
            if (mask.rock > 0) height += 18 * mask.rock;

            heightmap[y * size + x] = Math.max(0, Math.min(255, height));
        }
        if (y % rowYieldStep === 0 || y === size - 1) {
            postProgress(80 + (y / (size - 1)) * 7, `Building heightmap row ${y + 1}/${size}...`);
        }
    }

    const amplitudeBeforeSmoothing = measureAmplitude(heightmap);
    for (let i = 0; i < reliefProfile.smoothingPasses; i++) {
        postProgress(88 + i, `Smoothing terrain pass ${i + 1}/${reliefProfile.smoothingPasses}...`);
        smoothHeightmapAdaptive(heightmap, size, reliefProfile.slopePreservation);
    }
    const targetReliefAmplitude = getAmplitudePreservationTarget(amplitudeBeforeSmoothing, reliefProfile);
    preserveAmplitude(heightmap, targetReliefAmplitude, reliefProfile.minAmplitudePreservation);
    if (reliefProfile.waterBodyCarveDepth > 0) {
        applyWaterBodyPlane(heightmap, featureMask, size, reliefProfile);
        preserveAmplitudeOutsideWater(heightmap, featureMask, size, targetReliefAmplitude, reliefProfile.minAmplitudePreservation);
    }
    if (reliefProfile.waterwayCarveDepth > 0) {
        applyShallowWaterCarving(heightmap, featureMask, size, reliefProfile);
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
    const topologySignature = computeTopologySignature(heightmap, size, size, {
        stage: 'heightmapPreview',
        waterLevel,
        source: reliefProfile.source
    });

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
            heightVariation: reliefProfile.compileHeightRange,
            compileMinHeight: reliefProfile.compileMinHeight,
            compileMaxHeight: reliefProfile.compileMaxHeight,
            elevationSpanMeters: reliefProfile.elevationSpanMeters,
            reliefSource: reliefProfile.source,
            reliefProfile,
            waterLevel,
            metalSpots,
            metalStrength,
            geoSpots,
            startPositions,
            osmBounds: bounds,
            elevationMetadata
        },
        elevationMetadata,
        reliefProfile,
        topologySignature
    };
}

function computeTopologySignature(data, width, height, options = {}) {
    const sampleStepX = Math.max(1, Math.floor(width / 96));
    const sampleStepY = Math.max(1, Math.floor(height / 96));
    let minHeight = Infinity;
    let maxHeight = -Infinity;
    let sum = 0;
    let count = 0;
    const sampled = [];
    for (let y = 0; y < height; y += sampleStepY) {
        for (let x = 0; x < width; x += sampleStepX) {
            const value = Number(data[y * width + x]);
            if (!Number.isFinite(value)) continue;
            minHeight = Math.min(minHeight, value);
            maxHeight = Math.max(maxHeight, value);
            sum += value;
            count++;
            sampled.push({ x, y, value });
        }
    }
    if (!count) {
        minHeight = 0;
        maxHeight = 0;
    }
    const meanHeight = count ? sum / count : 0;
    let variance = 0;
    sampled.forEach(sample => {
        variance += (sample.value - meanHeight) ** 2;
    });
    let ruggedSum = 0;
    let ruggedCount = 0;
    for (let y = sampleStepY; y < height; y += sampleStepY) {
        for (let x = sampleStepX; x < width; x += sampleStepX) {
            const value = Number(data[y * width + x]);
            const left = Number(data[y * width + x - sampleStepX]);
            const up = Number(data[(y - sampleStepY) * width + x]);
            if (Number.isFinite(value) && Number.isFinite(left)) {
                ruggedSum += Math.abs(value - left);
                ruggedCount++;
            }
            if (Number.isFinite(value) && Number.isFinite(up)) {
                ruggedSum += Math.abs(value - up);
                ruggedCount++;
            }
        }
    }
    const profiles = sampleHeightProfileLines(data, width, height, 17);
    const westMean = averageProfileSlice(profiles.profileWestEast, 0, 0.35);
    const eastMean = averageProfileSlice(profiles.profileWestEast, 0.65, 1);
    const northMean = averageProfileSlice(profiles.profileNorthSouth, 0, 0.35);
    const southMean = averageProfileSlice(profiles.profileNorthSouth, 0.65, 1);
    const eastDelta = eastMean - westMean;
    const southDelta = southMean - northMean;
    const heightSpan = Math.max(0, maxHeight - minHeight);
    const threshold = Math.max(3, heightSpan * 0.08);
    let dominantGradient = 'mixed';
    if (Math.abs(eastDelta) > Math.abs(southDelta) && Math.abs(eastDelta) >= threshold) {
        dominantGradient = eastDelta > 0 ? 'east' : 'west';
    } else if (Math.abs(southDelta) >= threshold) {
        dominantGradient = southDelta > 0 ? 'south' : 'north';
    }
    return {
        stage: options.stage || 'heightmapPreview',
        width,
        height,
        minHeight,
        maxHeight,
        heightSpan,
        meanHeight,
        stdDevHeight: count ? Math.sqrt(variance / count) : 0,
        ruggedness: ruggedCount ? ruggedSum / ruggedCount : 0,
        dominantGradient,
        gradientScore: heightSpan > 0 ? Math.max(Math.abs(eastDelta), Math.abs(southDelta)) / heightSpan : 0,
        profileNorthSouth: profiles.profileNorthSouth,
        profileWestEast: profiles.profileWestEast,
        waterCoveragePct: Number.isFinite(options.waterLevel)
            ? sampled.filter(sample => sample.value <= options.waterLevel).length / Math.max(1, sampled.length) * 100
            : undefined,
        source: options.source || null
    };
}

function sampleHeightProfileLines(data, width, height, points) {
    const centerX = Math.floor(width / 2);
    const centerY = Math.floor(height / 2);
    const profileNorthSouth = [];
    const profileWestEast = [];
    for (let i = 0; i < points; i++) {
        const t = points <= 1 ? 0 : i / (points - 1);
        const x = Math.max(0, Math.min(width - 1, Math.round(t * (width - 1))));
        const y = Math.max(0, Math.min(height - 1, Math.round(t * (height - 1))));
        profileWestEast.push(Number(data[centerY * width + x]) || 0);
        profileNorthSouth.push(Number(data[y * width + centerX]) || 0);
    }
    return { profileNorthSouth, profileWestEast };
}

function averageProfileSlice(profile, startRatio, endRatio) {
    if (!profile.length) return 0;
    const start = Math.max(0, Math.floor(profile.length * startRatio));
    const end = Math.max(start + 1, Math.ceil(profile.length * endRatio));
    const slice = profile.slice(start, end);
    return slice.reduce((sum, value) => sum + value, 0) / slice.length;
}

function computeReliefProfile(elevationGrid, options = {}) {
    const metadata = normalizeElevationMetadata(elevationGrid);
    const finiteValues = (elevationGrid.values || []).filter(Number.isFinite);
    const minElevation = Number.isFinite(metadata.minElevationMeters)
        ? metadata.minElevationMeters
        : (finiteValues.length ? Math.min(...finiteValues) : 0);
    const maxElevation = Number.isFinite(metadata.maxElevationMeters)
        ? metadata.maxElevationMeters
        : (finiteValues.length ? Math.max(...finiteValues) : minElevation);
    const span = Math.max(0, maxElevation - minElevation);
    const heightScale = Number.isFinite(options.heightScale) ? Math.max(0.25, Math.min(8, options.heightScale)) : 1;
    const realSource = !metadata.synthetic && metadata.source === 'open-meteo';
    const source = realSource ? 'real' : (metadata.synthetic ? 'synthetic' : 'fallback');
    const compileHeightRange = realSource
        ? Math.max(220, Math.min(1400, Math.max(1, span) * heightScale))
        : Math.max(180, Math.min(520, Math.max(1, span) * Math.min(heightScale, 2.5)));
    const heightmapRange = realSource
        ? Math.max(120, Math.min(218, 90 + Math.sqrt(Math.max(1, span)) * 5.2 * Math.min(heightScale, 3)))
        : Math.max(92, Math.min(180, 80 + Math.sqrt(Math.max(1, span)) * 4));
    const maxResolution = Math.max(metadata.estimatedResolutionMetersX || 0, metadata.estimatedResolutionMetersY || 0);
    const coarse = maxResolution > 700 || (metadata.gridWidth || 0) < 32;
    const smoothingPasses = realSource ? (coarse ? 1 : 0) : 2;

    return {
        source,
        elevationMinMeters: minElevation,
        elevationMaxMeters: maxElevation,
        elevationSpanMeters: span,
        heightmapBase: 24,
        heightmapRange,
        heightScale,
        compileMinHeight: -Math.max(25, compileHeightRange * 0.08),
        compileMaxHeight: compileHeightRange,
        compileHeightRange,
        smoothingPasses,
        slopePreservation: realSource ? 0.82 : 0.65,
        minAmplitudePreservation: realSource ? 0.88 : 0.72,
        waterLevel: options.waterLevel || 58,
        waterBodyCarveDepth: realSource ? 12 : 18,
        waterwayCarveDepth: realSource ? 6 : 10,
        detailNoise: realSource ? 3 : 6
    };
}

function measureAmplitude(data) {
    let min = Infinity;
    let max = -Infinity;
    for (const value of data) {
        if (!Number.isFinite(value)) continue;
        min = Math.min(min, value);
        max = Math.max(max, value);
    }
    return Number.isFinite(min) && Number.isFinite(max) ? max - min : 0;
}

function preserveAmplitude(data, beforeAmplitude, minPreservation) {
    if (beforeAmplitude <= 0) return;
    const afterAmplitude = measureAmplitude(data);
    const target = beforeAmplitude * minPreservation;
    if (afterAmplitude >= target || afterAmplitude <= 0) return;
    let sum = 0;
    for (const value of data) sum += value;
    const mean = sum / data.length;
    const scale = target / afterAmplitude;
    for (let i = 0; i < data.length; i++) {
        data[i] = Math.max(0, Math.min(255, mean + (data[i] - mean) * scale));
    }
}

function getAmplitudePreservationTarget(amplitudeBeforeSmoothing, reliefProfile) {
    if (reliefProfile.source !== 'real') {
        return amplitudeBeforeSmoothing;
    }

    const span = Math.max(0, reliefProfile.elevationSpanMeters || 0);
    if (span < 8) {
        return amplitudeBeforeSmoothing;
    }

    if (span < 35) {
        const spanWeight = span / 35;
        return Math.max(amplitudeBeforeSmoothing, reliefProfile.heightmapRange * spanWeight);
    }

    return Math.max(amplitudeBeforeSmoothing, reliefProfile.heightmapRange);
}

function preserveAmplitudeOutsideWater(data, featureMask, size, beforeAmplitude, minPreservation) {
    if (beforeAmplitude <= 0) return;
    const targetAmplitude = beforeAmplitude * minPreservation;
    const currentAmplitude = measureAmplitude(data);
    if (currentAmplitude >= targetAmplitude || currentAmplitude <= 0) return;

    let globalMin = Infinity;
    let landMin = Infinity;
    let landMax = -Infinity;
    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const i = y * size + x;
            const value = data[i];
            if (!Number.isFinite(value)) continue;
            globalMin = Math.min(globalMin, value);
            const mask = sampleFeatureMask(featureMask, u, v);
            if (mask.water > 0) continue;
            landMin = Math.min(landMin, value);
            landMax = Math.max(landMax, value);
        }
    }
    if (!Number.isFinite(globalMin) || !Number.isFinite(landMin) || !Number.isFinite(landMax) || landMax <= landMin) return;

    const desiredLandMax = Math.min(255, globalMin + targetAmplitude);
    if (landMax >= desiredLandMax) return;

    const scale = (desiredLandMax - landMin) / (landMax - landMin);
    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const mask = sampleFeatureMask(featureMask, u, v);
            if (mask.water > 0) continue;
            const i = y * size + x;
            data[i] = Math.max(0, Math.min(255, landMin + (data[i] - landMin) * scale));
        }
    }
}

function smoothHeightmapAdaptive(data, size, slopePreservation) {
    const source = new Float32Array(data);
    for (let y = 1; y < size - 1; y++) {
        for (let x = 1; x < size - 1; x++) {
            const i = y * size + x;
            const center = source[i];
            const average = (
                source[i - 1] + source[i + 1] +
                source[i - size] + source[i + size] +
                center * 4
            ) / 8;
            const localSlope = Math.max(
                Math.abs(source[i - 1] - source[i + 1]),
                Math.abs(source[i - size] - source[i + size])
            );
            const blend = localSlope > 10 ? 1 - slopePreservation : 0.35;
            data[i] = center * (1 - blend) + average * blend;
        }
    }
}

function applyShallowWaterCarving(heightmap, featureMask, size, reliefProfile) {
    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const mask = sampleFeatureMask(featureMask, u, v);
            if (mask.waterway <= 0) continue;
            const i = y * size + x;
            const target = Math.max(0, reliefProfile.waterLevel - reliefProfile.waterwayCarveDepth);
            if (heightmap[i] > target) {
                heightmap[i] = Math.max(target, heightmap[i] - reliefProfile.waterwayCarveDepth * 0.45);
            }
        }
    }
}

function applyWaterBodyPlane(heightmap, featureMask, size, reliefProfile) {
    for (let y = 0; y < size; y++) {
        const v = y / (size - 1);
        for (let x = 0; x < size; x++) {
            const u = x / (size - 1);
            const mask = sampleFeatureMask(featureMask, u, v);
            if (mask.water <= 0) continue;
            const i = y * size + x;
            const waterPlane = Math.max(0, reliefProfile.waterLevel - reliefProfile.waterBodyCarveDepth * mask.water);
            heightmap[i] = Math.min(heightmap[i], waterPlane);
        }
    }
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
        waterway: b > 180 && r < 80 && g >= 80 && g < 180 ? 1 : 0,
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
