// Map Generation Web Worker — v2 with proper noise, domain warping, erosion

self.onmessage = function (e) {
    const params = e.data;
    const seed = params.seed || Date.now();

    try {
        self.postMessage({ type: 'progress', message: 'Generating heightmap...' });
        const heightmapData = generateHeightmap(
            params.size, params.terrainType, params.noiseStrength,
            params.heightVariation, params.waterLevel, params.smoothing, seed
        );

        self.postMessage({ type: 'progress', message: 'Generating texture map...' });
        const textureData = generateTextureMap(params.size, heightmapData, params.waterLevel, seed);

        self.postMessage({ type: 'progress', message: 'Analyzing terrain...' });
        const terrainAnalysis = analyzeTerrain(heightmapData, params.size, params.waterLevel);

        self.postMessage({ type: 'progress', message: 'Generating start positions...' });
        currentTerrainType = params.terrainType;
        const startPositions = generateStartPositions(params.size, params.playerCount, heightmapData, params.waterLevel, params.terrainType, seed);

        const minFairnessScore = 80;
        const maxRetries = 10;
        let resourceData, balance, retryCount = 0;

        do {
            self.postMessage({ type: 'progress', message: `Generating resources (attempt ${retryCount + 1})...` });
            resourceData = generateResourceMap(
                params.size, heightmapData, params.waterLevel,
                params.metalSpots, params.geoSpots, params.playerCount,
                params.metalStrength, terrainAnalysis, seed + retryCount
            );
            balance = calculateResourceBalance(resourceData, params.playerCount);
            retryCount++;
        } while (retryCount < maxRetries && parseFloat(balance.summary.overallFairness) < minFairnessScore);

        self.postMessage({
            type: 'complete',
            heightmapData: Array.from(heightmapData),
            textureData,
            resourceData,
            startPositions,
            balance,
            seed
        });
    } catch (error) {
        self.postMessage({ type: 'error', message: error.message });
    }
};

// ==========================================
// NOISE SYSTEM
// ==========================================

function seededRandom(seed) {
    let state = (seed ^ 0xdeadbeef) >>> 0;
    return () => {
        state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
        return state / 0x100000000;
    };
}

// Integer hash → float in [-1, 1]
function hash2D(ix, iy, seed) {
    let h = (seed | 0) + Math.imul(ix, 374761393) + Math.imul(iy, 668265263);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    h = h ^ (h >>> 16);
    return ((h & 0x7fffffff) / 0x3fffffff) - 1.0;
}

// Value noise with smooth Hermite interpolation
function valueNoise(x, y, seed) {
    const ix = Math.floor(x);
    const iy = Math.floor(y);
    const fx = x - ix;
    const fy = y - iy;

    // Quintic interpolation for C2 continuity
    const sx = fx * fx * fx * (fx * (fx * 6 - 15) + 10);
    const sy = fy * fy * fy * (fy * (fy * 6 - 15) + 10);

    const n00 = hash2D(ix,     iy,     seed);
    const n10 = hash2D(ix + 1, iy,     seed);
    const n01 = hash2D(ix,     iy + 1, seed);
    const n11 = hash2D(ix + 1, iy + 1, seed);

    const nx0 = n00 + sx * (n10 - n00);
    const nx1 = n01 + sx * (n11 - n01);
    return nx0 + sy * (nx1 - nx0);
}

// Fractional Brownian Motion
function fbm(x, y, seed, octaves, persistence, lacunarity) {
    let value = 0, amplitude = 1.0, frequency = 1.0, maxValue = 0;
    for (let i = 0; i < octaves; i++) {
        value += valueNoise(x * frequency, y * frequency, seed + i * 137) * amplitude;
        maxValue += amplitude;
        amplitude *= persistence;
        frequency *= lacunarity;
    }
    return value / maxValue;
}

// Ridged noise — sharp peaks and mountain ridges
function ridgedFbm(x, y, seed, octaves, persistence, lacunarity) {
    let value = 0, amplitude = 1.0, frequency = 1.0, maxValue = 0, prev = 1.0;
    for (let i = 0; i < octaves; i++) {
        let n = valueNoise(x * frequency, y * frequency, seed + i * 137);
        n = 1.0 - Math.abs(n);
        n = n * n * prev;
        prev = n;
        value += n * amplitude;
        maxValue += amplitude;
        amplitude *= persistence;
        frequency *= lacunarity;
    }
    return value / maxValue;
}

// Domain warping — feeds noise back into coordinates for organic shapes
function warpedFbm(x, y, seed, octaves, persistence, lacunarity, warpStrength) {
    const wx = fbm(x, y, seed + 100, 3, 0.5, 2.0) * warpStrength;
    const wy = fbm(x + 5.2, y + 1.3, seed + 200, 3, 0.5, 2.0) * warpStrength;
    return fbm(x + wx, y + wy, seed, octaves, persistence, lacunarity);
}

// ==========================================
// TERRAIN GENERATION
// ==========================================

function generateTerrainParams(terrainType, size, rng) {
    switch (terrainType) {
        case 'continental': {
            const lobeCount = 1 + Math.floor(rng() * 3); // 1–3 landmass lobes
            const lobes = [];
            for (let i = 0; i < lobeCount; i++) {
                lobes.push({
                    x: size * (0.25 + rng() * 0.5),
                    y: size * (0.25 + rng() * 0.5),
                    rx: size * (0.2 + rng() * 0.25),
                    ry: size * (0.2 + rng() * 0.25),
                    angle: rng() * Math.PI,
                });
            }
            return {
                lobes,
                noiseScale: 0.003 + rng() * 0.006,
                warpStrength: 1.5 + rng() * 3.5,
                ridgeMix: rng() * 0.35,
                erosionPasses: 2 + Math.floor(rng() * 3),
            };
        }
        case 'islands': {
            const count = 4 + Math.floor(rng() * 6); // 4–9 islands
            const islands = [];
            for (let i = 0; i < count; i++) {
                islands.push({
                    x: size * (0.08 + rng() * 0.84),
                    y: size * (0.08 + rng() * 0.84),
                    radius: size * (0.04 + rng() * 0.14),
                    peak: 0.55 + rng() * 0.45,
                    sharpness: 1.5 + rng() * 2.5,
                });
            }
            return {
                islands,
                noiseScale: 0.005 + rng() * 0.01,
                warpStrength: 2 + rng() * 4,
                seaFloorNoise: 0.02 + rng() * 0.06,
            };
        }
        case 'canyon': {
            const branchCount = 1 + Math.floor(rng() * 2);
            const branches = [{ angle: rng() * Math.PI, offset: 0 }];
            for (let i = 1; i < branchCount; i++) {
                branches.push({
                    angle: branches[0].angle + (0.3 + rng() * 0.8) * (rng() > 0.5 ? 1 : -1),
                    offset: size * (0.1 + rng() * 0.2) * (rng() > 0.5 ? 1 : -1),
                });
            }
            return {
                branches,
                width: 0.06 + rng() * 0.14,
                depth: 0.5 + rng() * 0.5,
                wallSharpness: 2 + rng() * 4,
                noiseScale: 0.004 + rng() * 0.008,
                warpStrength: 1.5 + rng() * 2.5,
                plateauHeight: 0.55 + rng() * 0.25,
            };
        }
        case 'hills':
            return {
                noiseScale: 0.004 + rng() * 0.008,
                baseHeight: 0.4 + rng() * 0.2,
                roughness: 0.3 + rng() * 0.6,
                persistence: 0.45 + rng() * 0.15,
                warpStrength: 1.5 + rng() * 3.0,
                ridgeMix: rng() * 0.5,
                erosionPasses: 2 + Math.floor(rng() * 3),
            };
        case 'flat':
            return {
                baseHeight: 0.45 + rng() * 0.25,
                noiseScale: 0.008 + rng() * 0.015,
                bumpiness: 0.03 + rng() * 0.18,
                warpStrength: 0.5 + rng() * 2.0,
                riverChance: rng(),
            };
        default:
            return {};
    }
}

function generateHeightmap(size, terrainType, noiseStrength, heightVariation, waterLevel, smoothing, seed) {
    const rng = seededRandom(seed);
    const params = generateTerrainParams(terrainType, size, rng);
    const data = new Float64Array(size * size);

    self.postMessage({ type: 'progress', message: 'Sculpting terrain...' });

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            let height;
            switch (terrainType) {
                case 'continental': height = genContinental(x, y, size, noiseStrength, seed, params); break;
                case 'islands':     height = genIslands(x, y, size, noiseStrength, seed, params); break;
                case 'canyon':      height = genCanyon(x, y, size, noiseStrength, seed, params); break;
                case 'hills':       height = genHills(x, y, size, noiseStrength, seed, params); break;
                case 'flat':        height = genFlat(x, y, size, noiseStrength, seed, params); break;
                default:            height = genHills(x, y, size, noiseStrength, seed, params);
            }
            data[y * size + x] = height * heightVariation;
        }
    }

    // Smoothing passes
    for (let i = 0; i < smoothing; i++) smoothHeightmap(data, size);

    // Thermal erosion — material slides down steep slopes
    const erosionPasses = params.erosionPasses || 2;
    if (erosionPasses > 0) {
        self.postMessage({ type: 'progress', message: 'Simulating erosion...' });
        thermalErosion(data, size, erosionPasses);
    }

    // Clamp to 0–255
    for (let i = 0; i < data.length; i++) {
        data[i] = Math.max(0, Math.min(255, data[i]));
    }

    return data;
}

// --- Terrain type functions ---

function genContinental(x, y, size, ns, seed, p) {
    // Combine elliptical lobes to form continent shape
    let landMask = 0;
    for (const lobe of p.lobes) {
        const cos = Math.cos(lobe.angle);
        const sin = Math.sin(lobe.angle);
        const dx = x - lobe.x;
        const dy = y - lobe.y;
        const rx = (dx * cos + dy * sin) / lobe.rx;
        const ry = (-dx * sin + dy * cos) / lobe.ry;
        const d = Math.sqrt(rx * rx + ry * ry);
        const falloff = Math.max(0, 1 - d);
        landMask = Math.max(landMask, falloff * falloff * (3 - 2 * falloff)); // smoothstep
    }

    // Organic terrain via domain-warped fBm + ridged mix
    const nx = x * p.noiseScale;
    const ny = y * p.noiseScale;
    const terrain = warpedFbm(nx, ny, seed, 6, 0.5, 2.0, p.warpStrength) * ns;
    const ridges = ridgedFbm(nx * 1.2, ny * 1.2, seed + 500, 4, 0.55, 2.1) * ns * p.ridgeMix;

    return Math.max(0, landMask * 0.7 + terrain * 0.5 + ridges * 0.3);
}

function genIslands(x, y, size, ns, seed, p) {
    let height = -0.1; // below sea level by default

    // Each island is a smooth dome, warped by noise
    const warpX = fbm(x * 0.005, y * 0.005, seed + 100, 3, 0.5, 2.0) * size * 0.08;
    const warpY = fbm(x * 0.005 + 5.2, y * 0.005 + 1.3, seed + 200, 3, 0.5, 2.0) * size * 0.08;
    const wx = x + warpX;
    const wy = y + warpY;

    for (const island of p.islands) {
        const dist = Math.sqrt((wx - island.x) ** 2 + (wy - island.y) ** 2);
        if (dist < island.radius * 1.5) {
            const t = Math.max(0, 1 - dist / island.radius);
            const dome = island.peak * Math.pow(t, 1.0 / island.sharpness);
            height = Math.max(height, dome);
        }
    }

    // Terrain detail on islands
    const detail = warpedFbm(x * p.noiseScale, y * p.noiseScale, seed, 5, 0.5, 2.0, p.warpStrength) * ns * 0.3;
    // Seafloor variation
    const seafloor = fbm(x * 0.003, y * 0.003, seed + 800, 3, 0.5, 2.0) * p.seaFloorNoise;

    return Math.max(0, height + detail + seafloor);
}

function genCanyon(x, y, size, ns, seed, p) {
    const cx = size / 2;
    const cy = size / 2;

    // Start with plateau
    let height = p.plateauHeight;

    // Carve each canyon branch with warped coordinates
    const warpX = fbm(x * 0.006, y * 0.006, seed + 300, 3, 0.5, 2.0) * size * 0.05;
    const warpY = fbm(x * 0.006 + 3.7, y * 0.006 + 8.1, seed + 400, 3, 0.5, 2.0) * size * 0.05;

    for (const branch of p.branches) {
        const cos = Math.cos(branch.angle);
        const sin = Math.sin(branch.angle);
        const perpDist = Math.abs((x + warpX - cx) * cos + (y + warpY - cy) * sin - branch.offset) / (size / 2);
        const canyonShape = Math.max(0, 1 - Math.pow(perpDist / p.width, p.wallSharpness));
        height -= canyonShape * p.depth;
    }

    // Surface detail
    const detail = warpedFbm(x * p.noiseScale, y * p.noiseScale, seed, 5, 0.5, 2.0, p.warpStrength) * ns * 0.4;
    return Math.max(0.02, height + detail);
}

function genHills(x, y, size, ns, seed, p) {
    const nx = x * p.noiseScale;
    const ny = y * p.noiseScale;

    // Domain-warped fBm for rolling hills
    const hills = warpedFbm(nx, ny, seed, 6, p.persistence, 2.0, p.warpStrength) * ns * 0.5;
    // Ridged component for dramatic peaks
    const ridges = ridgedFbm(nx * 1.3, ny * 1.3, seed + 600, 5, 0.5, 2.1) * ns * p.ridgeMix;
    // Fine detail for surface roughness
    const detail = fbm(nx * 4, ny * 4, seed + 1200, 3, 0.5, 2.0) * ns * 0.08 * p.roughness;

    return Math.max(0.05, p.baseHeight + hills + ridges + detail);
}

function genFlat(x, y, size, ns, seed, p) {
    let height = p.baseHeight;
    const noise = warpedFbm(x * p.noiseScale, y * p.noiseScale, seed, 4, 0.4, 2.0, p.warpStrength) * ns * p.bumpiness;

    // Occasional river-like channels
    if (p.riverChance > 0.5) {
        const riverNoise = fbm(x * 0.003, y * 0.003, seed + 900, 4, 0.5, 2.0);
        const river = Math.max(0, 1 - Math.abs(riverNoise) * 12);
        height -= river * 0.15;
    }

    return Math.max(0.05, height + noise);
}

// ==========================================
// EROSION + SMOOTHING
// ==========================================

function thermalErosion(data, size, iterations) {
    const talus = 3.5;
    for (let iter = 0; iter < iterations; iter++) {
        for (let y = 1; y < size - 1; y++) {
            for (let x = 1; x < size - 1; x++) {
                const idx = y * size + x;
                const h = data[idx];
                let maxDiff = 0, maxIdx = -1;

                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const nIdx = (y + dy) * size + (x + dx);
                        const diff = h - data[nIdx];
                        if (diff > maxDiff) { maxDiff = diff; maxIdx = nIdx; }
                    }
                }

                if (maxDiff > talus && maxIdx >= 0) {
                    const transfer = (maxDiff - talus) * 0.4;
                    data[idx] -= transfer;
                    data[maxIdx] += transfer;
                }
            }
        }
    }
}

function smoothHeightmap(data, size) {
    const buf = new Float64Array(data.length);
    for (let y = 1; y < size - 1; y++) {
        for (let x = 1; x < size - 1; x++) {
            const idx = y * size + x;
            let sum = 0;
            for (let dy = -1; dy <= 1; dy++)
                for (let dx = -1; dx <= 1; dx++)
                    sum += data[(y + dy) * size + (x + dx)];
            buf[idx] = sum / 9;
        }
    }
    for (let i = 0; i < data.length; i++) {
        if (buf[i] !== 0) data[i] = buf[i];
    }
}

// ==========================================
// TEXTURE GENERATION (smooth gradients + noise variation)
// ==========================================

function generateTextureMap(size, heightmapData, waterLevel, seed) {
    const textureData = new Array(size * size * 4);
    for (let i = 0; i < size * size; i++) {
        const x = i % size;
        const y = (i / size) | 0;
        const height = heightmapData[i];
        const idx = i * 4;
        const rel = height - waterLevel;

        // Color variation from noise
        const cn = valueNoise(x * 0.04, y * 0.04, seed + 3000) * 12;

        if (height < waterLevel) {
            const d = Math.min(1, (waterLevel - height) / 80);
            textureData[idx]     = clampByte(20 - d * 10 + cn * 0.3);
            textureData[idx + 1] = clampByte(55 - d * 20 + cn * 0.5);
            textureData[idx + 2] = clampByte(130 + d * 40);
        } else if (rel < 8) {
            const t = rel / 8;
            textureData[idx]     = clampByte(lerp(190, 85, t) + cn);
            textureData[idx + 1] = clampByte(lerp(175, 140, t) + cn);
            textureData[idx + 2] = clampByte(lerp(120, 50, t) + cn * 0.5);
        } else if (rel < 55) {
            const t = (rel - 8) / 47;
            textureData[idx]     = clampByte(lerp(65, 55, t) + cn);
            textureData[idx + 1] = clampByte(lerp(140, 115, t) + cn);
            textureData[idx + 2] = clampByte(lerp(40, 35, t) + cn * 0.5);
        } else if (rel < 95) {
            const t = (rel - 55) / 40;
            textureData[idx]     = clampByte(lerp(55, 100, t) + cn);
            textureData[idx + 1] = clampByte(lerp(110, 90, t) + cn);
            textureData[idx + 2] = clampByte(lerp(35, 55, t) + cn * 0.5);
        } else if (rel < 140) {
            const t = (rel - 95) / 45;
            textureData[idx]     = clampByte(lerp(100, 140, t) + cn);
            textureData[idx + 1] = clampByte(lerp(90, 130, t) + cn);
            textureData[idx + 2] = clampByte(lerp(60, 115, t) + cn * 0.5);
        } else {
            const t = Math.min(1, (rel - 140) / 35);
            textureData[idx]     = clampByte(lerp(180, 240, t) + cn * 0.3);
            textureData[idx + 1] = clampByte(lerp(185, 242, t) + cn * 0.3);
            textureData[idx + 2] = clampByte(lerp(195, 250, t));
        }
        textureData[idx + 3] = 255;
    }
    return textureData;
}

function lerp(a, b, t) { return a + (b - a) * t; }
function clampByte(v) { return Math.max(0, Math.min(255, Math.round(v))); }

// ==========================================
// TERRAIN ANALYSIS
// ==========================================

function analyzeTerrain(heightmapData, size, waterLevel) {
    return {
        hills: identifyHillsSimplified(heightmapData, size, waterLevel),
        valleys: findValleysSimplified(heightmapData, size, waterLevel),
        slope: null
    };
}

function identifyHillsSimplified(heightmapData, size, waterLevel) {
    const hills = [];
    const threshold = waterLevel + 80;
    const step = size >= 1024 ? 16 : 8;
    for (let y = step; y < size - step; y += step) {
        for (let x = step; x < size - step; x += step) {
            const h = heightmapData[y * size + x];
            if (h > threshold) {
                let isPeak = true;
                for (let dy = -step; dy <= step && isPeak; dy += step)
                    for (let dx = -step; dx <= step && isPeak; dx += step)
                        if ((dx || dy) && heightmapData[(y + dy) * size + (x + dx)] > h) isPeak = false;
                if (isPeak) hills.push({ x, y, height: h, radius: step * 2 });
            }
        }
    }
    return hills;
}

function findValleysSimplified(heightmapData, size, waterLevel) {
    const valleys = [];
    const maxH = waterLevel + 50;
    const step = size >= 1024 ? 16 : 8;
    for (let y = step; y < size - step; y += step) {
        for (let x = step; x < size - step; x += step) {
            const h = heightmapData[y * size + x];
            if (h > waterLevel + 5 && h < maxH) {
                let isValley = true;
                for (let dy = -step; dy <= step && isValley; dy += step)
                    for (let dx = -step; dx <= step && isValley; dx += step)
                        if ((dx || dy) && heightmapData[(y + dy) * size + (x + dx)] < h) isValley = false;
                if (isValley) valleys.push({ x, y, height: h, radius: step * 2 });
            }
        }
    }
    return valleys;
}

// ==========================================
// START POSITIONS
// ==========================================

let currentTerrainType = 'continental';

function generateStartPositions(size, playerCount, heightmapData, waterLevel, terrainType, seed) {
    const terrain = terrainType || currentTerrainType;
    if (terrain === 'canyon') return generateCanyonStartPositions(size, playerCount, heightmapData, waterLevel);
    if (terrain === 'islands') return generateIslandStartPositions(size, playerCount, heightmapData, waterLevel, seed);

    const radius = size * 0.35;
    const cx = size / 2, cy = size / 2;
    const rng = seededRandom(seed + 9999);
    const positions = [];

    for (let i = 0; i < playerCount; i++) {
        const angle = (i / playerCount) * 2 * Math.PI + rng() * 0.2;
        let x = Math.floor(cx + Math.cos(angle) * radius);
        let y = Math.floor(cy + Math.sin(angle) * radius);
        let attempts = 0;
        while (heightmapData[y * size + x] <= waterLevel && attempts < 50) {
            x = Math.floor(cx + Math.cos(angle) * (radius + rng() * 80 - 40));
            y = Math.floor(cy + Math.sin(angle) * (radius + rng() * 80 - 40));
            attempts++;
        }
        positions.push({ x, y, team: i + 1 });
    }
    return positions;
}

function generateCanyonStartPositions(size, playerCount, heightmapData, waterLevel) {
    const positions = [];
    const margin = size * 0.15;
    const topPlayers = Math.ceil(playerCount / 2);
    const bottomPlayers = playerCount - topPlayers;

    if (playerCount >= 5) {
        const fl = Math.min(4, playerCount), bl = playerCount - fl;
        const ft = Math.ceil(fl / 2), fb = fl - ft;
        for (let i = 0; i < ft; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / ft), size * 0.25, size, heightmapData, waterLevel, positions.length + 1));
        for (let i = 0; i < fb; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / fb), size * 0.75, size, heightmapData, waterLevel, positions.length + 1));
        const bt = Math.ceil(bl / 2), bb = bl - bt;
        for (let i = 0; i < bt; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / Math.max(bt, 1)), size * 0.10, size, heightmapData, waterLevel, positions.length + 1));
        for (let i = 0; i < bb; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / Math.max(bb, 1)), size * 0.90, size, heightmapData, waterLevel, positions.length + 1));
    } else {
        for (let i = 0; i < topPlayers; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / topPlayers), size * 0.15, size, heightmapData, waterLevel, positions.length + 1));
        for (let i = 0; i < bottomPlayers; i++) positions.push(findLandPosition(Math.floor(margin + (size - 2 * margin) * (i + 0.5) / bottomPlayers), size * 0.85, size, heightmapData, waterLevel, positions.length + 1));
    }
    return positions;
}

function generateIslandStartPositions(size, playerCount, heightmapData, waterLevel, seed) {
    const rng = seededRandom(seed + 77777);
    const candidates = [];
    const step = Math.floor(size / 20);
    for (let y = step; y < size - step; y += step)
        for (let x = step; x < size - step; x += step)
            if (heightmapData[y * size + x] > waterLevel + 20) candidates.push({ x, y });

    for (let i = candidates.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
    }

    const positions = [];
    const minDist = size * 0.2;
    for (const c of candidates) {
        if (positions.length >= playerCount) break;
        if (!positions.some(p => Math.sqrt((p.x - c.x) ** 2 + (p.y - c.y) ** 2) < minDist))
            positions.push({ x: c.x, y: c.y, team: positions.length + 1 });
    }
    while (positions.length < playerCount) {
        const c = candidates[positions.length % candidates.length] || { x: size / 2, y: size / 2 };
        positions.push({ x: c.x, y: c.y, team: positions.length + 1 });
    }
    return positions;
}

function findLandPosition(startX, startY, size, heightmapData, waterLevel, team) {
    let x = Math.floor(startX), y = Math.floor(startY), attempts = 0;
    while (heightmapData[y * size + x] <= waterLevel && attempts < 100) {
        const r = attempts * 5, a = attempts * 0.5;
        x = Math.max(10, Math.min(size - 10, Math.floor(startX + Math.cos(a) * r)));
        y = Math.max(10, Math.min(size - 10, Math.floor(startY + Math.sin(a) * r)));
        attempts++;
    }
    return { x, y, team };
}

// ==========================================
// VORONOI TERRITORIES
// ==========================================

function generateVoronoiTerritories(startPositions, size) {
    const territories = new Int8Array(size * size);
    const step = size >= 1024 ? 4 : (size >= 512 ? 2 : 1);
    for (let y = 0; y < size; y += step) {
        for (let x = 0; x < size; x += step) {
            let nearest = 0, minD = Infinity;
            for (let i = 0; i < startPositions.length; i++) {
                const d = Math.sqrt((x - startPositions[i].x) ** 2 + (y - startPositions[i].y) ** 2);
                if (d < minD) { minD = d; nearest = i; }
            }
            for (let dy = 0; dy < step && y + dy < size; dy++)
                for (let dx = 0; dx < step && x + dx < size; dx++)
                    territories[(y + dy) * size + (x + dx)] = nearest;
        }
    }
    return { territories, startPositions };
}

// ==========================================
// RESOURCE GENERATION
// ==========================================

function generateResourceMap(size, heightmapData, waterLevel, metalSpots, geoSpots, playerCount, metalStrength, terrainAnalysis, seed) {
    const resourceData = { metalSpots: [], geoSpots: [], size };
    const startPositions = generateStartPositions(size, playerCount, heightmapData, waterLevel, currentTerrainType, seed);
    const voronoiData = generateVoronoiTerritories(startPositions, size);
    const territories = voronoiData.territories;

    const baseSpotsPerPlayer = Math.floor(metalSpots / playerCount);
    const extraSpots = metalSpots % playerCount;

    for (let player = 0; player < playerCount; player++) {
        const spotsForPlayer = baseSpotsPerPlayer + (player < extraSpots ? 1 : 0);
        const scored = [];
        const step = size >= 1024 ? 16 : (size >= 512 ? 8 : 4);

        for (let y = 0; y < size; y += step)
            for (let x = 0; x < size; x += step)
                if (territories[y * size + x] === player && heightmapData[y * size + x] > waterLevel + 10)
                    scored.push({ x, y, score: ((heightmapData[y * size + x] - waterLevel) / 255) * 30 + Math.random() * 20 });

        scored.sort((a, b) => b.score - a.score);
        const maxScore = scored.length > 0 ? scored[0].score : 1;

        for (let i = 0, si = 0; i < spotsForPlayer && si < scored.length; si++) {
            const { x, y, score } = scored[si];
            if (!resourceData.metalSpots.some(s => Math.sqrt((x - s.x) ** 2 + (y - s.y) ** 2) < size * 0.05)) {
                const val = calcMetalValue(size, playerCount, metalStrength, score, maxScore);
                resourceData.metalSpots.push({ x, y, value: val, territory: player });
                i++;
            }
        }
    }

    // Geo spots
    const geoStep = Math.max(size / 50, 8);
    const geoCandidates = [];
    for (let y = 2; y < size - 2; y += geoStep)
        for (let x = 2; x < size - 2; x += geoStep)
            if (heightmapData[y * size + x] > waterLevel + 30)
                geoCandidates.push({ x, y, score: ((heightmapData[y * size + x] - waterLevel) / 255) * 40 + Math.random() * 15 });

    geoCandidates.sort((a, b) => b.score - a.score);
    const maxGeo = geoCandidates.length > 0 ? geoCandidates[0].score : 1;
    let placed = 0;
    for (const c of geoCandidates) {
        if (placed >= geoSpots) break;
        if (!resourceData.geoSpots.some(s => Math.sqrt((c.x - s.x) ** 2 + (c.y - s.y) ** 2) < size * 0.12)) {
            resourceData.geoSpots.push({ x: c.x, y: c.y, value: calcGeoValue(c.score, maxGeo) });
            placed++;
        }
    }

    resourceData.territories = territories;
    return resourceData;
}

function calcMetalValue(mapSize, playerCount, metalStrength, score, maxScore) {
    const sizeMul = ({ 512: 0.9, 1024: 1.0, 2048: 1.1 })[mapSize] || 1.0;
    const base = metalStrength * sizeMul * (1.0 - (playerCount - 2) * 0.05) * (0.8 + (score / maxScore) * 0.4);
    return Math.max(1.0, Math.min(5.0, base * (0.85 + Math.random() * 0.3)));
}

function calcGeoValue(score, maxScore) {
    return Math.max(150, Math.min(550, 200 + (score / maxScore) * 300 + Math.random() * 50 - 25));
}

// ==========================================
// RESOURCE BALANCE
// ==========================================

function calculateResourceBalance(resourceData, playerCount) {
    const balance = { perPlayer: [], fairnessScore: 0, summary: {} };
    for (let p = 0; p < playerCount; p++) {
        const spots = resourceData.metalSpots.filter(s => s.territory === p);
        const total = spots.reduce((sum, s) => sum + s.value, 0);
        balance.perPlayer.push({ player: p + 1, metalSpotCount: spots.length, totalMetalValue: total, avgMetalPerSpot: spots.length > 0 ? total / spots.length : 0 });
    }

    const cv = vals => {
        if (!vals.length) return 0;
        const m = vals.reduce((a, b) => a + b, 0) / vals.length;
        if (m === 0) return 0;
        return (Math.sqrt(vals.reduce((s, v) => s + (v - m) ** 2, 0) / vals.length) / m) * 100;
    };

    const spotCV = cv(balance.perPlayer.map(p => p.metalSpotCount));
    const metalCV = cv(balance.perPlayer.map(p => p.totalMetalValue));
    const f = c => Math.max(0, 100 - c * 4);
    balance.fairnessScore = f(metalCV) * 0.6 + f(spotCV) * 0.4;
    balance.summary = {
        spotDistributionCV: spotCV.toFixed(1),
        metalDistributionCV: metalCV.toFixed(1),
        overallFairness: balance.fairnessScore.toFixed(1),
        totalMetalSpots: resourceData.metalSpots.length,
        avgMetalPerSpot: balance.perPlayer.length > 0
            ? (balance.perPlayer.reduce((s, p) => s + p.totalMetalValue, 0) / resourceData.metalSpots.length).toFixed(2) : '0'
    };
    return balance;
}
