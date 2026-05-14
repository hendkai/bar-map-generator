const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function makeBounds() {
    return {
        getSouth: () => 10,
        getWest: () => 20,
        getNorth: () => 11,
        getEast: () => 22
    };
}

function loadBrowserElevationFunctions(fetchImpl) {
    const html = fs.readFileSync('bar_map_generator.html', 'utf8');
    const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
        .map(match => match[1])
        .find(text => text.includes('async function fetchElevationGridForBounds'));
    const start = script.indexOf('function boundsToPlainObject');
    const end = script.indexOf('async function buildTerrainFromOsm');
    const elevationCode = script.slice(start, end);
    const progress = [];
    const sandbox = {
        fetch: fetchImpl,
        URLSearchParams,
        Math,
        Date,
        Number,
        SyntaxError,
        Error,
        noise2D: (x, y) => Math.sin(x * 12.9898 + y * 78.233),
        updateOsmProgress: (percent, message) => progress.push({ percent, message }),
        setTimeout,
        clearTimeout,
        globalThis: null
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(`${elevationCode}
        globalThis.__exports = {
            fetchElevationGridForBounds,
            fetchElevationGrid,
            createSyntheticElevationGrid,
            createElevationGrid,
            formatElevationGridStatus,
            createElevationCacheKey,
            getElevationGridSize,
            computeTopologySignature,
            compareTopologySignature,
            computeBoundsSignature,
            getTopologyReferenceRegions
        };
    `, sandbox, { filename: 'bar_map_generator.html:elevation' });
    return { api: sandbox.__exports, progress };
}

function loadWorkerFunctions() {
    const code = fs.readFileSync('osm-worker.js', 'utf8');
    const messages = [];
    const sandbox = {
        importScripts: () => {},
        self: {
            postMessage: message => messages.push(message)
        },
        Math,
        Float32Array,
        Uint8ClampedArray,
        Boolean,
        Number,
        smoothHeightmap: () => {},
        generateStartPositions: () => [{ x: 1, y: 1 }],
        analyzeTerrain: () => ({ landRatio: 1 }),
        generateResourceMap: size => new Uint8ClampedArray(size * size * 4),
        currentTerrainType: null,
        globalThis: null
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(`${code}
        globalThis.__exports = {
            buildTerrainFromOsmWorker,
            normalizeElevationMetadata,
            sampleElevation,
            computeReliefProfile,
            measureAmplitude,
            computeTopologySignature
        };
    `, sandbox, { filename: 'osm-worker.js' });
    return { api: sandbox.__exports, messages, worker: sandbox.self };
}

function loadBrowserExportFunctions() {
    const html = fs.readFileSync('bar_map_generator.html', 'utf8');
    const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
        .map(match => match[1])
        .find(text => text.includes('function generatePythonBuildScript'));
    const start = script.indexOf('function generatePythonBuildScript');
    const helperStart = script.indexOf('function generateBARMapInfo');
    const helperEnd = script.indexOf('function generateBARMapHelper');
    const code = `${script.slice(start, script.indexOf('function generateBatchScript'))}
${script.slice(helperStart, helperEnd)}`;
    const sandbox = {
        Number,
        Math,
        Date,
        Blob: function () {},
        mapConfig: null,
        resourceData: { metalSpots: [], geoSpots: [] },
        globalThis: null
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(`${code}
        globalThis.__exports = {
            generatePythonBuildScript,
            generateBARMapInfo
        };
    `, sandbox, { filename: 'bar_map_generator.html:export' });
    return sandbox;
}

async function testBrowserOpenMeteoSuccess() {
    const { api } = loadBrowserElevationFunctions(async url => {
        assert(url.startsWith('https://api.open-meteo.com/v1/elevation?'));
        return {
            ok: true,
            text: async () => JSON.stringify({ elevation: [100, 110, 120, 130] })
        };
    });

    const grid = await api.fetchElevationGridForBounds(makeBounds(), {
        targetGridSize: 2,
        maxBatchSize: 4,
        allowSyntheticFallback: true
    });

    assert.deepStrictEqual(Array.from(grid.values), [100, 110, 120, 130]);
    assert.strictEqual(grid.synthetic, false);
    assert.strictEqual(grid.metadata.source, 'open-meteo');
    assert.strictEqual(grid.metadata.providerName, 'Open-Meteo Elevation API');
    assert.strictEqual(grid.metadata.sampleCount, 4);
    assert.strictEqual(grid.metadata.minElevationMeters, 100);
    assert.strictEqual(grid.metadata.maxElevationMeters, 130);
    assert.deepStrictEqual({ ...grid.metadata.bounds }, { south: 10, west: 20, north: 11, east: 22 });
    assert.strictEqual(grid.metadata.cacheKey, 'open-meteo:10.000000:20.000000:11.000000:22.000000:2x2');
    assert.match(api.formatElevationGridStatus(grid), /Open-Meteo Elevation API real API elevation/);
    assert.strictEqual(api.getElevationGridSize(10), 64);
    assert.strictEqual(api.getElevationGridSize(30), 48);
}

async function testBrowserFallbacks() {
    {
        const { api } = loadBrowserElevationFunctions(async () => {
            throw new Error('network down');
        });
        const grid = await api.fetchElevationGridForBounds(makeBounds(), {
            targetGridSize: 2,
            allowSyntheticFallback: true
        });
        assert.strictEqual(grid.synthetic, true);
        assert.strictEqual(grid.metadata.source, 'synthetic-fallback');
        assert.match(grid.metadata.fallbackReason, /request failed: network down/);
        assert.match(api.formatElevationGridStatus(grid), /Fallback reason:/);
    }

    {
        const { api } = loadBrowserElevationFunctions(async () => ({
            ok: true,
            text: async () => JSON.stringify({ elevation: [100, null, '', 130] })
        }));
        const grid = await api.fetchElevationGridForBounds(makeBounds(), {
            targetGridSize: 2,
            maxBatchSize: 4,
            allowSyntheticFallback: true
        });
        assert.strictEqual(grid.synthetic, true);
        assert.match(grid.metadata.fallbackReason, /non-numeric elevation data/);
        assert.strictEqual(grid.values.length, 4);
    }

    {
        const { api, progress } = loadBrowserElevationFunctions(async () => ({
            ok: false,
            status: 429,
            text: async () => ''
        }));
        const grid = await api.fetchElevationGridForBounds(makeBounds(), {
            targetGridSize: 2,
            allowSyntheticFallback: true
        });
        assert.strictEqual(grid.synthetic, true);
        assert.match(grid.metadata.fallbackReason, /HTTP 429/);
        assert(progress.some(entry => entry.message.includes('rate limit')));
    }
}

async function testWorkerUsesElevationAndPassesMetadata() {
    const { api, messages, worker } = loadWorkerFunctions();
    assert.strictEqual(api.sampleElevation({
        gridWidth: 3,
        gridHeight: 2,
        values: [0, 10, 20, 30, 40, 50]
    }, 0.5, 1), 40);

    const metadata = {
        source: 'open-meteo',
        providerName: 'Open-Meteo Elevation API',
        gridWidth: 2,
        gridHeight: 2,
        sampleCount: 4,
        minElevationMeters: 0,
        maxElevationMeters: 300,
        synthetic: false,
        fallbackReason: null
    };
    const featureMask = {
        width: 2,
        height: 2,
        data: new Uint8ClampedArray(2 * 2 * 4)
    };
    const generated = await api.buildTerrainFromOsmWorker(
        { south: 10, west: 20, north: 11, east: 22 },
        featureMask,
        { gridWidth: 2, gridHeight: 2, values: [0, 100, 200, 300], metadata },
        { size: 8, playerCount: 2, heightScale: 1, metalSpots: 0, metalStrength: 1, geoSpots: 0, seed: 1 }
    );

    assert.deepStrictEqual({ ...generated.elevationMetadata }, metadata);
    assert.deepStrictEqual({ ...generated.config.elevationMetadata }, metadata);
    assert.strictEqual(generated.config.reliefSource, 'real');
    assert.strictEqual(generated.config.elevationSpanMeters, 300);
    assert(Number.isFinite(generated.config.compileMinHeight));
    assert(Number.isFinite(generated.config.compileMaxHeight));
    assert(generated.heightmap[generated.heightmap.length - 1] > generated.heightmap[0]);

    await worker.onmessage({
        data: {
            bounds: { south: 10, west: 20, north: 11, east: 22 },
            featureMask,
            elevationGrid: { gridWidth: 2, gridHeight: 2, values: [0, 100, 200, 300], metadata },
            config: { size: 8, playerCount: 2, heightScale: 1, metalSpots: 0, metalStrength: 1, geoSpots: 0, seed: 1 }
        }
    });
    const complete = messages.find(message => message.type === 'complete');
    assert(complete.reliefProfile);
    assert.strictEqual(complete.reliefProfile.source, 'real');
    assert(complete.topologySignature);
    assert.strictEqual(complete.topologySignature.stage, 'heightmapPreview');
    assert(complete.topologySignature.heightSpan > 0);
}

function testTopologySignaturesAndReferenceComparison() {
    const { api } = loadBrowserElevationFunctions(async () => {
        throw new Error('not used');
    });
    const sharedCatalog = JSON.parse(fs.readFileSync('topology_reference_regions.json', 'utf8'));
    assert.deepStrictEqual(
        JSON.parse(JSON.stringify(api.getTopologyReferenceRegions())),
        sharedCatalog
    );
    const eastGradient = Array.from({ length: 16 }, (_, i) => (i % 4) * 20);
    const eastSignature = api.computeTopologySignature(eastGradient, 4, 4, { stage: 'heightmapPreview' });
    assert.strictEqual(eastSignature.dominantGradient, 'east');
    assert.strictEqual(eastSignature.heightSpan, 60);

    const flatSignature = api.computeTopologySignature(new Array(16).fill(42), 4, 4, { stage: 'heightmapPreview' });
    const reference = api.getTopologyReferenceRegions()[0];
    const correctIssues = api.compareTopologySignature(reference, [], api.computeBoundsSignature(reference.bounds));
    assert.strictEqual(correctIssues.length, 0);

    const flatIssues = api.compareTopologySignature(
        reference,
        [Object.assign({}, flatSignature, { stage: 'heightmapPreview' })],
        api.computeBoundsSignature(reference.bounds)
    );
    assert(flatIssues.some(issue => issue.code === 'relief-too-flat'));

    const wrongBounds = { south: 52.4, west: 13.3, north: 52.5, east: 13.5 };
    const boundsIssues = api.compareTopologySignature(reference, [], api.computeBoundsSignature(wrongBounds));
    assert(boundsIssues.some(issue => issue.code === 'bounds-mismatch'));

    const sourceWrongGradient = Object.assign({}, eastSignature, {
        stage: 'sourceElevation',
        heightSpan: reference.expected.elevationSpanM,
        dominantGradient: reference.expected.dominantGradient === 'east' ? 'west' : 'east',
        gradientScore: 0.5
    });
    const gradientIssues = api.compareTopologySignature(reference, [sourceWrongGradient], api.computeBoundsSignature(reference.bounds));
    assert(gradientIssues.some(issue => issue.code === 'gradient-mismatch'));

    const exportIssues = api.compareTopologySignature(
        reference,
        [
            Object.assign({}, eastSignature, { stage: 'heightmapPreview', heightSpan: 100, dominantGradient: 'east' }),
            Object.assign({}, eastSignature, { stage: 'barExport', heightSpan: 20, dominantGradient: 'west' })
        ],
        api.computeBoundsSignature(reference.bounds)
    );
    assert(exportIssues.some(issue => issue.code === 'preview-export-divergence'));
}

async function testReliefAmplitudeAndSmallSpanCompileRange() {
    const { api } = loadWorkerFunctions();
    const featureMask = {
        width: 2,
        height: 2,
        data: new Uint8ClampedArray(2 * 2 * 4)
    };
    const baseConfig = { size: 32, playerCount: 2, heightScale: 2.5, metalSpots: 0, metalStrength: 1, geoSpots: 0, seed: 1 };
    const realMeta = (min, max) => ({
        source: 'open-meteo',
        providerName: 'Open-Meteo Elevation API',
        gridWidth: 4,
        gridHeight: 4,
        sampleCount: 16,
        minElevationMeters: min,
        maxElevationMeters: max,
        synthetic: false,
        estimatedResolutionMetersX: 80,
        estimatedResolutionMetersY: 80
    });
    const flat = await api.buildTerrainFromOsmWorker(
        {},
        featureMask,
        { gridWidth: 4, gridHeight: 4, values: new Array(16).fill(100), metadata: realMeta(100, 100) },
        baseConfig
    );
    const mountainous = await api.buildTerrainFromOsmWorker(
        {},
        featureMask,
        { gridWidth: 4, gridHeight: 4, values: Array.from({ length: 16 }, (_, i) => 100 + i * (800 / 15)), metadata: realMeta(100, 900) },
        baseConfig
    );
    const hillyProfile = api.computeReliefProfile(
        { gridWidth: 4, gridHeight: 4, values: [180, 210, 230, 260], metadata: realMeta(180, 260) },
        { heightScale: 2.5, waterLevel: 58 }
    );

    assert(api.measureAmplitude(mountainous.heightmap) > api.measureAmplitude(flat.heightmap) + 90);
    assert(api.measureAmplitude(flat.heightmap) < 20, `flat real terrain was amplified to ${api.measureAmplitude(flat.heightmap)}`);
    assert(hillyProfile.compileHeightRange >= 220);
    assert.strictEqual(hillyProfile.compileMaxHeight, 220);
}

async function testWaterCarvingAndReliefPreservation() {
    const { api } = loadWorkerFunctions();
    const dryMask = { width: 2, height: 2, data: new Uint8ClampedArray(2 * 2 * 4) };
    const waterwayMaskData = new Uint8ClampedArray(2 * 2 * 4);
    waterwayMaskData[(3 * 4) + 1] = 128;
    waterwayMaskData[(3 * 4) + 2] = 255;
    const waterwayMask = { width: 2, height: 2, data: waterwayMaskData };
    const waterBodyMaskData = new Uint8ClampedArray(2 * 2 * 4);
    waterBodyMaskData[(3 * 4) + 2] = 255;
    const waterBodyMask = { width: 2, height: 2, data: waterBodyMaskData };
    const metadata = {
        source: 'open-meteo',
        gridWidth: 4,
        gridHeight: 4,
        sampleCount: 16,
        minElevationMeters: 100,
        maxElevationMeters: 900,
        synthetic: false,
        estimatedResolutionMetersX: 80,
        estimatedResolutionMetersY: 80
    };
    const grid = { gridWidth: 4, gridHeight: 4, values: Array.from({ length: 16 }, (_, i) => 100 + i * (800 / 15)), metadata };
    const config = { size: 32, playerCount: 2, heightScale: 2.5, metalSpots: 0, metalStrength: 1, geoSpots: 0, seed: 1 };
    const dry = await api.buildTerrainFromOsmWorker({}, dryMask, grid, config);
    const waterway = await api.buildTerrainFromOsmWorker({}, waterwayMask, grid, config);
    const waterBody = await api.buildTerrainFromOsmWorker({}, waterBodyMask, grid, config);
    const amplitudeRatio = api.measureAmplitude(waterBody.heightmap) / api.measureAmplitude(dry.heightmap);
    const carved = dry.heightmap[dry.heightmap.length - 1] - waterway.heightmap[waterway.heightmap.length - 1];

    assert(amplitudeRatio > 0.75, `water collapsed relief ratio to ${amplitudeRatio}`);
    assert(carved > 0 && carved < 40, `waterway carving depth was ${carved}`);
    assert(waterBody.heightmap[waterBody.heightmap.length - 1] <= waterBody.config.waterLevel);
}

async function testHighTerrainWaterBodyPreservesGlobalRelief() {
    const { api } = loadWorkerFunctions();
    const dryMask = { width: 4, height: 4, data: new Uint8ClampedArray(4 * 4 * 4) };
    const highWaterMaskData = new Uint8ClampedArray(4 * 4 * 4);
    for (let y = 2; y < 4; y++) {
        for (let x = 0; x < 4; x++) {
            highWaterMaskData[((y * 4 + x) * 4) + 2] = 255;
        }
    }
    const highWaterMask = { width: 4, height: 4, data: highWaterMaskData };
    const metadata = {
        source: 'open-meteo',
        gridWidth: 4,
        gridHeight: 4,
        sampleCount: 16,
        minElevationMeters: 100,
        maxElevationMeters: 900,
        synthetic: false,
        estimatedResolutionMetersX: 80,
        estimatedResolutionMetersY: 80
    };
    const grid = {
        gridWidth: 4,
        gridHeight: 4,
        values: Array.from({ length: 16 }, (_, i) => 100 + i * (800 / 15)),
        metadata
    };
    const config = { size: 32, playerCount: 2, heightScale: 2.5, metalSpots: 0, metalStrength: 1, geoSpots: 0, seed: 1 };
    const dry = await api.buildTerrainFromOsmWorker({}, dryMask, grid, config);
    const highWater = await api.buildTerrainFromOsmWorker({}, highWaterMask, grid, config);
    const amplitudeRatio = api.measureAmplitude(highWater.heightmap) / api.measureAmplitude(dry.heightmap);

    assert(amplitudeRatio > 0.75, `high-terrain water collapsed relief ratio to ${amplitudeRatio}`);
    assert(highWater.heightmap[highWater.heightmap.length - 1] <= highWater.config.waterLevel);
}

function testBrowserExportHeightBounds() {
    const sandbox = loadBrowserExportFunctions();
    sandbox.mapConfig = {
        size: 1024,
        terrainType: 'osm',
        playerCount: 2,
        waterLevel: 58,
        heightVariation: 999,
        compileMinHeight: -25,
        compileMaxHeight: 307.95,
        startPositions: [{ x: 128, y: 128 }, { x: 896, y: 896 }]
    };
    const script = sandbox.__exports.generatePythonBuildScript('relief_test');
    const mapinfo = sandbox.__exports.generateBARMapInfo();

    assert.match(script, /COMPILE_MIN_HEIGHT = -25\.00/);
    assert.match(script, /COMPILE_MAX_HEIGHT = 307\.95/);
    assert.match(script, /"-x", f"\{COMPILE_MAX_HEIGHT:\.2f\}", "-n", f"\{COMPILE_MIN_HEIGHT:\.2f\}"/);
    assert.match(mapinfo, /minheight = -25/);
    assert.match(mapinfo, /maxheight = 307\.95/);
}

(async () => {
    await testBrowserOpenMeteoSuccess();
    await testBrowserFallbacks();
    await testWorkerUsesElevationAndPassesMetadata();
    await testReliefAmplitudeAndSmallSpanCompileRange();
    await testWaterCarvingAndReliefPreservation();
    await testHighTerrainWaterBodyPreservesGlobalRelief();
    testTopologySignaturesAndReferenceComparison();
    testBrowserExportHeightBounds();
    console.log('elevation-pipeline-harness: all assertions passed');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
