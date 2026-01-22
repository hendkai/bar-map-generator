// Map Generation Web Worker
// Runs heavy computation in background thread to prevent UI freeze

self.onmessage = function (e) {
    const params = e.data;

    try {
        self.postMessage({ type: 'progress', message: 'Generating heightmap...' });
        const heightmapData = generateHeightmap(
            params.size, params.terrainType, params.noiseStrength,
            params.heightVariation, params.waterLevel, params.smoothing
        );

        self.postMessage({ type: 'progress', message: 'Generating texture map...' });
        const textureData = generateTextureMap(params.size, heightmapData, params.waterLevel);

        self.postMessage({ type: 'progress', message: 'Analyzing terrain...' });
        const terrainAnalysis = analyzeTerrain(heightmapData, params.size, params.waterLevel);

        self.postMessage({ type: 'progress', message: 'Generating start positions...' });
        currentTerrainType = params.terrainType; // Store for use in generateResourceMap
        const startPositions = generateStartPositions(params.size, params.playerCount, heightmapData, params.waterLevel, params.terrainType);

        // Resource generation with retry for fairness
        const minFairnessScore = 80;
        const maxRetries = 10;
        let resourceData, balance;
        let retryCount = 0;

        do {
            self.postMessage({ type: 'progress', message: `Generating resources (attempt ${retryCount + 1})...` });
            resourceData = generateResourceMap(
                params.size, heightmapData, params.waterLevel,
                params.metalSpots, params.geoSpots, params.playerCount,
                params.metalStrength, terrainAnalysis
            );
            balance = calculateResourceBalance(resourceData, params.playerCount);
            retryCount++;
        } while (retryCount < maxRetries && parseFloat(balance.summary.overallFairness) < minFairnessScore);

        self.postMessage({
            type: 'complete',
            heightmapData: Array.from(heightmapData),
            textureData: textureData,
            resourceData: resourceData,
            startPositions: startPositions,
            balance: balance
        });
    } catch (error) {
        self.postMessage({ type: 'error', message: error.message });
    }
};

// === TERRAIN GENERATION ===

function generateHeightmap(size, terrainType, noiseStrength, heightVariation, waterLevel, smoothing) {
    const data = new Array(size * size);

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            const index = y * size + x;
            let height = 0;

            switch (terrainType) {
                case 'continental':
                    height = generateContinentalTerrain(x, y, size, noiseStrength);
                    break;
                case 'islands':
                    height = generateIslandTerrain(x, y, size, noiseStrength);
                    break;
                case 'canyon':
                    height = generateCanyonTerrain(x, y, size, noiseStrength);
                    break;
                case 'hills':
                    height = generateHillyTerrain(x, y, size, noiseStrength);
                    break;
                case 'flat':
                    height = generateFlatTerrain(x, y, size, noiseStrength);
                    break;
            }

            data[index] = Math.max(0, Math.min(255, height * heightVariation));
        }
    }

    for (let i = 0; i < smoothing; i++) {
        smoothHeightmap(data, size);
    }

    return data;
}

function generateContinentalTerrain(x, y, size, noiseStrength) {
    const centerX = size / 2;
    const centerY = size / 2;
    const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
    const dist = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
    const baseHeight = 1 - (dist / maxDist) * 0.7;
    const noise = (noise2D(x * 0.01, y * 0.01) + noise2D(x * 0.005, y * 0.005) * 0.5) * noiseStrength;
    return Math.max(0, baseHeight + noise);
}

function generateIslandTerrain(x, y, size, noiseStrength) {
    const islands = [
        { x: size * 0.3, y: size * 0.3, radius: size * 0.2 },
        { x: size * 0.7, y: size * 0.7, radius: size * 0.2 },
        { x: size * 0.2, y: size * 0.8, radius: size * 0.15 },
        { x: size * 0.8, y: size * 0.2, radius: size * 0.15 }
    ];
    let height = 0;
    islands.forEach(island => {
        const dist = Math.sqrt((x - island.x) ** 2 + (y - island.y) ** 2);
        if (dist < island.radius) {
            height = Math.max(height, 1 - (dist / island.radius));
        }
    });
    const noise = noise2D(x * 0.01, y * 0.01) * noiseStrength;
    return Math.max(0, height + noise);
}

function generateCanyonTerrain(x, y, size, noiseStrength) {
    const canyonCenter = size / 2;
    const distFromCenter = Math.abs(y - canyonCenter) / (size / 2);
    let height = distFromCenter;
    const noise = noise2D(x * 0.008, y * 0.008) * noiseStrength;
    return Math.max(0.1, height + noise);
}

function generateHillyTerrain(x, y, size, noiseStrength) {
    const noise1 = noise2D(x * 0.008, y * 0.008);
    const noise2 = noise2D(x * 0.015, y * 0.015) * 0.5;
    const noise3 = noise2D(x * 0.03, y * 0.03) * 0.25;
    // Base at 0.6 ensures most terrain is above water level
    return Math.max(0.4, (noise1 + noise2 + noise3) * noiseStrength * 0.5 + 0.65);
}

function generateFlatTerrain(x, y, size, noiseStrength) {
    const noise = noise2D(x * 0.02, y * 0.02) * noiseStrength * 0.3;
    return 0.6 + noise;
}

function noise2D(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
    return (n - Math.floor(n)) * 2 - 1;
}

function smoothHeightmap(data, size) {
    const newData = [...data];
    for (let y = 1; y < size - 1; y++) {
        for (let x = 1; x < size - 1; x++) {
            const index = y * size + x;
            let sum = 0;
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    sum += data[(y + dy) * size + (x + dx)];
                }
            }
            newData[index] = sum / 9;
        }
    }
    for (let i = 0; i < data.length; i++) {
        data[i] = newData[i];
    }
}

// === TEXTURE GENERATION ===

function generateTextureMap(size, heightmapData, waterLevel) {
    const textureData = new Array(size * size * 4);
    for (let i = 0; i < size * size; i++) {
        const height = heightmapData[i];
        const index = i * 4;
        if (height < waterLevel) {
            textureData[index] = 30; textureData[index + 1] = 100; textureData[index + 2] = 200;
        } else if (height < waterLevel + 20) {
            textureData[index] = 255; textureData[index + 1] = 230; textureData[index + 2] = 150;
        } else if (height < waterLevel + 80) {
            textureData[index] = 50; textureData[index + 1] = 150; textureData[index + 2] = 50;
        } else if (height < waterLevel + 120) {
            textureData[index] = 120; textureData[index + 1] = 120; textureData[index + 2] = 120;
        } else {
            textureData[index] = 240; textureData[index + 1] = 240; textureData[index + 2] = 255;
        }
        textureData[index + 3] = 255;
    }
    return textureData;
}

// === TERRAIN ANALYSIS ===

function analyzeTerrain(heightmapData, size, waterLevel) {
    // Simplified analysis for worker - skip slope calculation for performance
    const hills = identifyHillsSimplified(heightmapData, size, waterLevel);
    const valleys = findValleysSimplified(heightmapData, size, waterLevel);
    return { hills, valleys, slope: null };
}

function identifyHillsSimplified(heightmapData, size, waterLevel) {
    const hills = [];
    const heightThreshold = waterLevel + 80;
    const step = size >= 1024 ? 16 : 8;

    for (let y = step; y < size - step; y += step) {
        for (let x = step; x < size - step; x += step) {
            const index = y * size + x;
            const height = heightmapData[index];
            if (height > heightThreshold) {
                let isPeak = true;
                for (let dy = -step; dy <= step && isPeak; dy += step) {
                    for (let dx = -step; dx <= step && isPeak; dx += step) {
                        if (dx === 0 && dy === 0) continue;
                        if (heightmapData[(y + dy) * size + (x + dx)] > height) {
                            isPeak = false;
                        }
                    }
                }
                if (isPeak) {
                    hills.push({ x, y, height, radius: step * 2 });
                }
            }
        }
    }
    return hills;
}

function findValleysSimplified(heightmapData, size, waterLevel) {
    const valleys = [];
    const maxHeightThreshold = waterLevel + 50;
    const step = size >= 1024 ? 16 : 8;

    for (let y = step; y < size - step; y += step) {
        for (let x = step; x < size - step; x += step) {
            const index = y * size + x;
            const height = heightmapData[index];
            if (height > waterLevel + 5 && height < maxHeightThreshold) {
                let isValley = true;
                for (let dy = -step; dy <= step && isValley; dy += step) {
                    for (let dx = -step; dx <= step && isValley; dx += step) {
                        if (dx === 0 && dy === 0) continue;
                        if (heightmapData[(y + dy) * size + (x + dx)] < height) {
                            isValley = false;
                        }
                    }
                }
                if (isValley) {
                    valleys.push({ x, y, height, radius: step * 2 });
                }
            }
        }
    }
    return valleys;
}

// Store current terrain type for start position generation
let currentTerrainType = 'continental';

function generateStartPositions(size, playerCount, heightmapData, waterLevel, terrainType = null) {
    const terrain = terrainType || currentTerrainType;
    const positions = [];

    // For canyon terrain: place spawns on top and bottom (avoid water in middle)
    if (terrain === 'canyon') {
        return generateCanyonStartPositions(size, playerCount, heightmapData, waterLevel);
    }

    // For islands terrain: place spawns on islands
    if (terrain === 'islands') {
        return generateIslandStartPositions(size, playerCount, heightmapData, waterLevel);
    }

    // Default: circular placement around center
    const radius = size * 0.35;
    const centerX = size / 2;
    const centerY = size / 2;

    for (let i = 0; i < playerCount; i++) {
        const angle = (i / playerCount) * 2 * Math.PI;
        let x = Math.floor(centerX + Math.cos(angle) * radius);
        let y = Math.floor(centerY + Math.sin(angle) * radius);

        let attempts = 0;
        while (heightmapData[y * size + x] <= waterLevel && attempts < 50) {
            x = Math.floor(centerX + Math.cos(angle) * (radius + Math.random() * 50 - 25));
            y = Math.floor(centerY + Math.sin(angle) * (radius + Math.random() * 50 - 25));
            attempts++;
        }
        positions.push({ x, y, team: i + 1 });
    }
    return positions;
}

function generateCanyonStartPositions(size, playerCount, heightmapData, waterLevel) {
    const positions = [];
    const margin = size * 0.15; // Stay away from edges
    const topY = size * 0.15;   // Top land area
    const bottomY = size * 0.85; // Bottom land area

    // For 2-4 players: split evenly top/bottom
    // For 5-8 players: 4 frontline (inner), rest backline (outer)

    const topPlayers = Math.ceil(playerCount / 2);
    const bottomPlayers = playerCount - topPlayers;

    // Determine if we need frontline/backline (for 5+ players)
    const useFrontlineBackline = playerCount >= 5;

    if (useFrontlineBackline) {
        // 4 frontline, rest backline
        const frontlinePlayers = Math.min(4, playerCount);
        const backlinePlayers = playerCount - frontlinePlayers;

        const frontTopY = size * 0.25;  // Frontline closer to middle
        const frontBottomY = size * 0.75;
        const backTopY = size * 0.10;   // Backline near edge
        const backBottomY = size * 0.90;

        // Frontline: 2 top, 2 bottom (or split for odd)
        const frontTop = Math.ceil(frontlinePlayers / 2);
        const frontBottom = frontlinePlayers - frontTop;

        // Place frontline top
        for (let i = 0; i < frontTop; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / frontTop);
            const y = Math.floor(frontTopY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }

        // Place frontline bottom
        for (let i = 0; i < frontBottom; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / frontBottom);
            const y = Math.floor(frontBottomY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }

        // Backline: split remaining players top/bottom
        const backTop = Math.ceil(backlinePlayers / 2);
        const backBottom = backlinePlayers - backTop;

        // Place backline top
        for (let i = 0; i < backTop; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / Math.max(backTop, 1));
            const y = Math.floor(backTopY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }

        // Place backline bottom
        for (let i = 0; i < backBottom; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / Math.max(backBottom, 1));
            const y = Math.floor(backBottomY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }
    } else {
        // Simple top/bottom split for 2-4 players
        for (let i = 0; i < topPlayers; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / topPlayers);
            const y = Math.floor(topY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }

        for (let i = 0; i < bottomPlayers; i++) {
            const x = Math.floor(margin + (size - 2 * margin) * (i + 0.5) / bottomPlayers);
            const y = Math.floor(bottomY);
            positions.push(findLandPosition(x, y, size, heightmapData, waterLevel, positions.length + 1));
        }
    }

    return positions;
}

function generateIslandStartPositions(size, playerCount, heightmapData, waterLevel) {
    // Island positions based on the 4 main islands
    const islandCenters = [
        { x: size * 0.3, y: size * 0.3 },
        { x: size * 0.7, y: size * 0.7 },
        { x: size * 0.2, y: size * 0.8 },
        { x: size * 0.8, y: size * 0.2 }
    ];

    const positions = [];
    for (let i = 0; i < playerCount; i++) {
        const island = islandCenters[i % islandCenters.length];
        positions.push(findLandPosition(island.x, island.y, size, heightmapData, waterLevel, i + 1));
    }
    return positions;
}

function findLandPosition(startX, startY, size, heightmapData, waterLevel, team) {
    let x = Math.floor(startX);
    let y = Math.floor(startY);

    // Search for land if starting position is water
    let attempts = 0;
    while (heightmapData[y * size + x] <= waterLevel && attempts < 100) {
        // Spiral search outward
        const searchRadius = attempts * 5;
        const angle = attempts * 0.5;
        x = Math.floor(startX + Math.cos(angle) * searchRadius);
        y = Math.floor(startY + Math.sin(angle) * searchRadius);

        // Clamp to map bounds
        x = Math.max(10, Math.min(size - 10, x));
        y = Math.max(10, Math.min(size - 10, y));
        attempts++;
    }

    return { x, y, team };
}

// === VORONOI TERRITORIES ===

function generateVoronoiTerritories(startPositions, size) {
    const territories = new Int8Array(size * size);
    const step = size >= 1024 ? 4 : (size >= 512 ? 2 : 1);

    for (let y = 0; y < size; y += step) {
        for (let x = 0; x < size; x += step) {
            let nearestPlayer = 0;
            let minDistance = Infinity;

            for (let i = 0; i < startPositions.length; i++) {
                const pos = startPositions[i];
                const dist = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
                if (dist < minDistance) {
                    minDistance = dist;
                    nearestPlayer = i;
                }
            }

            for (let dy = 0; dy < step && y + dy < size; dy++) {
                for (let dx = 0; dx < step && x + dx < size; dx++) {
                    territories[(y + dy) * size + (x + dx)] = nearestPlayer;
                }
            }
        }
    }
    return { territories, startPositions };
}

// === RESOURCE GENERATION ===

function generateResourceMap(size, heightmapData, waterLevel, metalSpots, geoSpots, playerCount, metalStrength, terrainAnalysis) {
    const resourceData = { metalSpots: [], geoSpots: [], size };
    const startPositions = generateStartPositions(size, playerCount, heightmapData, waterLevel);
    const voronoiData = generateVoronoiTerritories(startPositions, size);
    const territories = voronoiData.territories;

    const baseSpotsPerPlayer = Math.floor(metalSpots / playerCount);
    const extraSpots = metalSpots % playerCount;
    const spotsPerTerritory = new Array(playerCount).fill(0);
    const metalPerTerritory = new Array(playerCount).fill(0);

    // Metal spots per territory
    for (let player = 0; player < playerCount; player++) {
        const spotsForPlayer = baseSpotsPerPlayer + (player < extraSpots ? 1 : 0);
        const scoredPositions = [];
        const sampleStep = size >= 1024 ? 16 : (size >= 512 ? 8 : 4);

        for (let y = 0; y < size; y += sampleStep) {
            for (let x = 0; x < size; x += sampleStep) {
                const index = y * size + x;
                if (territories[index] === player) {
                    const height = heightmapData[index];
                    if (height > waterLevel + 10) {
                        const score = calculateStrategicScoreSimple(x, y, height, terrainAnalysis, size, waterLevel);
                        scoredPositions.push({ x, y, score });
                    }
                }
            }
        }

        scoredPositions.sort((a, b) => b.score - a.score);
        const maxStrategicScore = scoredPositions.length > 0 ? scoredPositions[0].score : 1.0;

        for (let i = 0; i < spotsForPlayer && scoredPositions.length > 0; i++) {
            let placedSpot = false;
            let searchIndex = 0;

            while (!placedSpot && searchIndex < scoredPositions.length) {
                const { x, y, score } = scoredPositions[searchIndex];
                let tooClose = false;

                for (const spot of resourceData.metalSpots) {
                    const dist = Math.sqrt((x - spot.x) ** 2 + (y - spot.y) ** 2);
                    if (dist < size * 0.05) {
                        tooClose = true;
                        break;
                    }
                }

                if (!tooClose) {
                    const metalValue = calculateMetalSpotValue(size, playerCount, metalStrength, score, maxStrategicScore);
                    resourceData.metalSpots.push({ x, y, value: metalValue, territory: player });
                    spotsPerTerritory[player]++;
                    metalPerTerritory[player] += metalValue;
                    placedSpot = true;
                }
                searchIndex++;
            }
        }
    }

    // Geo spots
    const candidateStep = Math.max(size / 50, 8);
    const candidates = [];

    for (let y = 2; y < size - 2; y += candidateStep) {
        for (let x = 2; x < size - 2; x += candidateStep) {
            const height = heightmapData[y * size + x];
            if (height > waterLevel + 30) {
                const score = calculateGeoScoreSimple(x, y, height, terrainAnalysis, size, waterLevel, territories, playerCount);
                candidates.push({ x, y, height, score });
            }
        }
    }

    candidates.sort((a, b) => b.score - a.score);
    let placedGeoSpots = 0;
    const maxGeoScore = candidates.length > 0 ? candidates[0].score : 1.0;

    for (const candidate of candidates) {
        if (placedGeoSpots >= geoSpots) break;
        let tooClose = false;

        for (const spot of resourceData.geoSpots) {
            const dist = Math.sqrt((candidate.x - spot.x) ** 2 + (candidate.y - spot.y) ** 2);
            if (dist < size * 0.12) {
                tooClose = true;
                break;
            }
        }

        if (!tooClose) {
            const geoValue = calculateGeoVentValue(candidate.score, maxGeoScore);
            resourceData.geoSpots.push({ x: candidate.x, y: candidate.y, value: geoValue });
            placedGeoSpots++;
        }
    }

    resourceData.territories = territories;
    resourceData.spotsPerTerritory = spotsPerTerritory;
    return resourceData;
}

function calculateStrategicScoreSimple(x, y, height, terrainAnalysis, size, waterLevel) {
    let score = ((height - waterLevel) / 255) * 30;
    score += Math.random() * 20;
    return Math.max(0, score);
}

function calculateGeoScoreSimple(x, y, height, terrainAnalysis, size, waterLevel, territories, playerCount) {
    let score = ((height - waterLevel) / 255) * 40;
    score += Math.random() * 15;
    return Math.max(0, score);
}

function calculateMetalSpotValue(mapSize, playerCount, metalStrength, strategicScore, maxScore) {
    const sizeMultipliers = { 512: 0.9, 1024: 1.0, 2048: 1.1 };
    const sizeMultiplier = sizeMultipliers[mapSize] || 1.0;
    const playerAdjustment = 1.0 - (playerCount - 2) * 0.05;
    const strategicMultiplier = 0.8 + (strategicScore / maxScore) * 0.4;
    const baseValue = metalStrength * sizeMultiplier * playerAdjustment * strategicMultiplier;
    const variation = 0.85 + Math.random() * 0.3;
    return Math.max(1.0, Math.min(5.0, baseValue * variation));
}

function calculateGeoVentValue(strategicScore, maxScore) {
    const baseValue = 200;
    const strategicBonus = (strategicScore / maxScore) * 300;
    const randomVariation = Math.random() * 50 - 25;
    return Math.max(150, Math.min(550, baseValue + strategicBonus + randomVariation));
}

// === RESOURCE BALANCE ===

function calculateResourceBalance(resourceData, playerCount) {
    const balance = { perPlayer: [], territoryAnalysis: [], fairnessScore: 0, summary: {} };

    for (let player = 0; player < playerCount; player++) {
        const playerSpots = resourceData.metalSpots.filter(spot => spot.territory === player);
        const totalMetal = playerSpots.reduce((sum, spot) => sum + spot.value, 0);
        const avgMetalPerSpot = playerSpots.length > 0 ? totalMetal / playerSpots.length : 0;
        balance.perPlayer.push({
            player: player + 1,
            metalSpotCount: playerSpots.length,
            totalMetalValue: totalMetal,
            avgMetalPerSpot
        });
    }

    const calculateCV = (values) => {
        if (values.length === 0) return 0;
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        if (mean === 0) return 0;
        const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
        return (Math.sqrt(variance) / mean) * 100;
    };

    const spotCounts = balance.perPlayer.map(p => p.metalSpotCount);
    const metalTotals = balance.perPlayer.map(p => p.totalMetalValue);

    const spotCV = calculateCV(spotCounts);
    const metalCV = calculateCV(metalTotals);

    const cvToFairness = (cv) => Math.max(0, 100 - (cv * 4));
    const spotFairness = cvToFairness(spotCV);
    const metalFairness = cvToFairness(metalCV);

    balance.fairnessScore = metalFairness * 0.6 + spotFairness * 0.4;

    balance.summary = {
        spotDistributionCV: spotCV.toFixed(1),
        metalDistributionCV: metalCV.toFixed(1),
        overallFairness: balance.fairnessScore.toFixed(1),
        totalMetalSpots: resourceData.metalSpots.length,
        avgMetalPerSpot: metalTotals.length > 0 ? (metalTotals.reduce((a, b) => a + b, 0) / resourceData.metalSpots.length).toFixed(2) : '0'
    };

    return balance;
}
