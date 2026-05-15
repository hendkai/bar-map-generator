const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function loadTextureExportFunctions() {
    const html = fs.readFileSync('bar_map_generator.html', 'utf8');
    const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
        .map(match => match[1])
        .find(text => text.includes('function canvasToBmpBlob'));
    const start = script.indexOf('function canvasToBmpBlob');
    const end = script.indexOf('function generateReadme');
    const code = script.slice(start, end);
    const sandbox = {
        Blob,
        DataView,
        ArrayBuffer,
        Math,
        Error,
        globalThis: null
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(`${code}
        globalThis.__exports = {
            canvasToBmpBlob,
            validateExportedTextureBmp
        };
    `, sandbox, { filename: 'bar_map_generator.html:texture-export' });
    return sandbox.__exports;
}

function makeCanvas(width, height) {
    const data = new Uint8ClampedArray(width * height * 4);
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const index = (y * width + x) * 4;
            data[index] = (x * 17 + y * 3) & 255;
            data[index + 1] = (y * 29) & 255;
            data[index + 2] = (x * 7 + y * 11) & 255;
            data[index + 3] = 255;
        }
    }
    return {
        width,
        height,
        getContext: () => ({
            getImageData: (sourceX = 0, sourceY = 0, sourceWidth = width, sourceHeight = height) => {
                const slice = new Uint8ClampedArray(sourceWidth * sourceHeight * 4);
                for (let y = 0; y < sourceHeight; y++) {
                    for (let x = 0; x < sourceWidth; x++) {
                        const src = ((sourceY + y) * width + sourceX + x) * 4;
                        const dst = (y * sourceWidth + x) * 4;
                        slice[dst] = data[src];
                        slice[dst + 1] = data[src + 1];
                        slice[dst + 2] = data[src + 2];
                        slice[dst + 3] = data[src + 3];
                    }
                }
                return { data: slice };
            }
        }),
        sourceData: data
    };
}

async function blobToBuffer(blob) {
    return Buffer.from(await blob.arrayBuffer());
}

function parseBmp(buffer) {
    assert.strictEqual(buffer.toString('ascii', 0, 2), 'BM');
    const width = buffer.readInt32LE(18);
    const signedHeight = buffer.readInt32LE(22);
    const height = Math.abs(signedHeight);
    const bitsPerPixel = buffer.readUInt16LE(28);
    const pixelOffset = buffer.readUInt32LE(10);
    const rowStride = Math.ceil((width * bitsPerPixel) / 32) * 4;
    return {
        width,
        height,
        bitsPerPixel,
        pixelOffset,
        rowStride,
        topDown: signedHeight < 0
    };
}

function readBmpRgb(buffer, info, x, y) {
    const storedY = info.topDown ? y : info.height - 1 - y;
    const offset = info.pixelOffset + storedY * info.rowStride + x * 3;
    return [buffer[offset + 2], buffer[offset + 1], buffer[offset]];
}

function sourceRgb(canvas, x, y) {
    const index = (y * canvas.width + x) * 4;
    return [
        canvas.sourceData[index],
        canvas.sourceData[index + 1],
        canvas.sourceData[index + 2]
    ];
}

async function testBmpHeaderStrideAndRows() {
    const { canvasToBmpBlob, validateExportedTextureBmp } = loadTextureExportFunctions();
    const canvas = makeCanvas(17, 19);
    const blob = canvasToBmpBlob(canvas);
    await validateExportedTextureBmp(blob, canvas.width, canvas.height);
    const buffer = await blobToBuffer(blob);
    const info = parseBmp(buffer);

    assert.strictEqual(info.width, 17);
    assert.strictEqual(info.height, 19);
    assert.strictEqual(info.bitsPerPixel, 24);
    assert.strictEqual(info.rowStride, 52);
    assert.strictEqual(buffer.length, info.pixelOffset + info.rowStride * info.height);

    for (const y of [0, 1, 8, 9, 18]) {
        assert.deepStrictEqual(readBmpRgb(buffer, info, 0, y), sourceRgb(canvas, 0, y));
        assert.deepStrictEqual(readBmpRgb(buffer, info, 8, y), sourceRgb(canvas, 8, y));
        assert.deepStrictEqual(readBmpRgb(buffer, info, 16, y), sourceRgb(canvas, 16, y));
    }

    assert.notDeepStrictEqual(readBmpRgb(buffer, info, 0, 0), readBmpRgb(buffer, info, 0, 8));
    assert.notDeepStrictEqual(readBmpRgb(buffer, info, 0, 8), readBmpRgb(buffer, info, 0, 16));
}

async function testLargeTextureFormulaSize() {
    const { canvasToBmpBlob, validateExportedTextureBmp } = loadTextureExportFunctions();
    const mapUnits = 16;
    const textureSize = 512 * mapUnits;
    const canvas = makeCanvas(64, 64);
    const blob = canvasToBmpBlob(canvas);

    await assert.rejects(
        () => validateExportedTextureBmp(blob, textureSize, textureSize),
        /expected 8192x8192/
    );
}

async function main() {
    await testBmpHeaderStrideAndRows();
    await testLargeTextureFormulaSize();
    console.log('Texture export harness passed');
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});
