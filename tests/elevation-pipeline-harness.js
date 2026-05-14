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
            createElevationCacheKey
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
            sampleElevation
        };
    `, sandbox, { filename: 'osm-worker.js' });
    return { api: sandbox.__exports, messages };
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
    const { api } = loadWorkerFunctions();
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
    assert(generated.heightmap[generated.heightmap.length - 1] > generated.heightmap[0]);
}

(async () => {
    await testBrowserOpenMeteoSuccess();
    await testBrowserFallbacks();
    await testWorkerUsesElevationAndPassesMetadata();
    console.log('elevation-pipeline-harness: all assertions passed');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
