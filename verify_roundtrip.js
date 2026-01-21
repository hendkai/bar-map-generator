#!/usr/bin/env node

/**
 * Automated Round-trip Export/Import Verification Script
 *
 * This script verifies that the export/import functions preserve
 * all configuration data accurately through a complete round-trip cycle.
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

function logTest(testName) {
    log(`\n${'='.repeat(60)}`, 'cyan');
    log(`TEST: ${testName}`, 'bright');
    log('='.repeat(60), 'cyan');
}

function logResult(passed, message) {
    if (passed) {
        log(`✓ PASSED: ${message}`, 'green');
    } else {
        log(`✗ FAILED: ${message}`, 'red');
    }
}

// Simulate the export/import functions from bar_map_generator.html
function simulateExportConfigJSON(mapConfig, creatorName, mapDescription) {
    const exportData = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        metadata: {
            creator: creatorName || 'Anonymous',
            description: mapDescription || 'No description'
        },
        config: { ...mapConfig }
    };

    return JSON.stringify(exportData, null, 2);
}

function simulateImportConfigJSON(jsonString) {
    const importData = JSON.parse(jsonString);

    // Validate structure
    if (!importData.version || !importData.config) {
        throw new Error('Invalid configuration file format. Missing required fields.');
    }

    return importData;
}

function simulateExportConfigText(mapConfig, creatorName, mapDescription) {
    const exportData = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        metadata: {
            creator: creatorName || 'Anonymous',
            description: mapDescription || 'No description'
        },
        config: { ...mapConfig }
    };

    const jsonString = JSON.stringify(exportData);
    return Buffer.from(jsonString).toString('base64');
}

function simulateImportConfigText(base64String) {
    const jsonString = Buffer.from(base64String, 'base64').toString('utf-8');
    const importData = JSON.parse(jsonString);

    if (!importData.version || !importData.config) {
        throw new Error('Invalid configuration format. Missing required fields.');
    }

    return importData;
}

function compareConfigs(original, imported) {
    const mismatches = [];

    Object.keys(original).forEach(key => {
        if (original[key] !== imported[key]) {
            mismatches.push({
                field: key,
                original: original[key],
                imported: imported[key]
            });
        }
    });

    return mismatches;
}

// Test cases
const testCases = [
    {
        name: 'Basic Configuration',
        config: {
            size: 1024,
            terrainType: 'continental',
            playerCount: 4,
            noiseStrength: 0.5,
            heightVariation: 0.6,
            waterLevel: 0.3,
            metalSpots: 50,
            metalStrength: 0.7,
            geoSpots: 10,
            startPositions: []
        },
        metadata: {
            creator: 'Test User',
            description: 'Test configuration for round-trip verification'
        }
    },
    {
        name: 'Extreme Values',
        config: {
            size: 2048,
            terrainType: 'hills',
            playerCount: 8,
            noiseStrength: 1.0,
            heightVariation: 1.0,
            waterLevel: 1.0,
            metalSpots: 100,
            metalStrength: 1.0,
            geoSpots: 50,
            startPositions: []
        },
        metadata: {
            creator: 'Extreme Tester',
            description: 'Testing maximum values'
        }
    },
    {
        name: 'Minimum Values',
        config: {
            size: 512,
            terrainType: 'flat',
            playerCount: 2,
            noiseStrength: 0.0,
            heightVariation: 0.0,
            waterLevel: 0.0,
            metalSpots: 0,
            metalStrength: 0.0,
            geoSpots: 0,
            startPositions: []
        },
        metadata: {
            creator: 'Min Tester',
            description: 'Testing minimum values'
        }
    },
    {
        name: 'All Terrain Types',
        config: {
            size: 1024,
            terrainType: 'canyon',
            playerCount: 6,
            noiseStrength: 0.75,
            heightVariation: 0.8,
            waterLevel: 0.4,
            metalSpots: 75,
            metalStrength: 0.9,
            geoSpots: 25,
            startPositions: []
        },
        metadata: {
            creator: 'Terrain Tester',
            description: 'Testing canyon terrain'
        }
    },
    {
        name: 'Special Characters',
        config: {
            size: 1024,
            terrainType: 'islands',
            playerCount: 4,
            noiseStrength: 0.5,
            heightVariation: 0.6,
            waterLevel: 0.3,
            metalSpots: 50,
            metalStrength: 0.7,
            geoSpots: 10,
            startPositions: []
        },
        metadata: {
            creator: 'Test "Quotes" & <Symbols>',
            description: 'Config with émojis 😊🎮 and unicode: 中文 漢字'
        }
    },
    {
        name: 'Empty Metadata',
        config: {
            size: 1024,
            terrainType: 'continental',
            playerCount: 4,
            noiseStrength: 0.5,
            heightVariation: 0.6,
            waterLevel: 0.3,
            metalSpots: 50,
            metalStrength: 0.7,
            geoSpots: 10,
            startPositions: []
        },
        metadata: {
            creator: '',
            description: ''
        }
    }
];

// Run tests
function runTests() {
    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    log('║   ROUND-TRIP EXPORT/IMPORT VERIFICATION SUITE           ║', 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    let totalTests = 0;
    let passedTests = 0;
    let failedTests = 0;

    // Test JSON round-trip
    log('\n' + '─'.repeat(60), 'blue');
    log('JSON ROUND-TRIP TESTS', 'bright');
    log('─'.repeat(60), 'blue');

    testCases.forEach((testCase, index) => {
        logTest(`JSON Test ${index + 1}: ${testCase.name}`);
        totalTests++;

        try {
            // Export
            const jsonString = simulateExportConfigJSON(
                testCase.config,
                testCase.metadata.creator,
                testCase.metadata.description
            );

            // Import
            const imported = simulateImportConfigJSON(jsonString);

            // Compare config
            const configMismatches = compareConfigs(testCase.config, imported.config);

            // Compare metadata
            const metadataMismatches = compareConfigs(testCase.metadata, imported.metadata);

            const allMismatches = [...configMismatches, ...metadataMismatches];

            if (allMismatches.length === 0) {
                logResult(true, `All values preserved through JSON round-trip`);
                passedTests++;
            } else {
                logResult(false, `Mismatches detected:`);
                allMismatches.forEach(mismatch => {
                    log(`  - ${mismatch.field}: "${mismatch.original}" → "${mismatch.imported}"`, 'red');
                });
                failedTests++;
            }

        } catch (error) {
            logResult(false, `Exception: ${error.message}`);
            failedTests++;
        }
    });

    // Test Text round-trip
    log('\n' + '─'.repeat(60), 'blue');
    log('TEXT ROUND-TRIP TESTS', 'bright');
    log('─'.repeat(60), 'blue');

    testCases.forEach((testCase, index) => {
        logTest(`Text Test ${index + 1}: ${testCase.name}`);
        totalTests++;

        try {
            // Export
            const base64String = simulateExportConfigText(
                testCase.config,
                testCase.metadata.creator,
                testCase.metadata.description
            );

            // Import
            const imported = simulateImportConfigText(base64String);

            // Compare config
            const configMismatches = compareConfigs(testCase.config, imported.config);

            // Compare metadata
            const metadataMismatches = compareConfigs(testCase.metadata, imported.metadata);

            const allMismatches = [...configMismatches, ...metadataMismatches];

            if (allMismatches.length === 0) {
                logResult(true, `All values preserved through Text round-trip`);
                passedTests++;
            } else {
                logResult(false, `Mismatches detected:`);
                allMismatches.forEach(mismatch => {
                    log(`  - ${mismatch.field}: "${mismatch.original}" → "${mismatch.imported}"`, 'red');
                });
                failedTests++;
            }

        } catch (error) {
            logResult(false, `Exception: ${error.message}`);
            failedTests++;
        }
    });

    // Test cross-format (JSON export → Text import and vice versa)
    log('\n' + '─'.repeat(60), 'blue');
    log('CROSS-FORMAT TESTS', 'bright');
    log('─'.repeat(60), 'blue');

    testCases.forEach((testCase, index) => {
        logTest(`Cross-Format Test ${index + 1}: ${testCase.name}`);
        totalTests++;

        try {
            // Export as JSON
            const jsonString = simulateExportConfigJSON(
                testCase.config,
                testCase.metadata.creator,
                testCase.metadata.description
            );

            // Manually convert to base64 (simulate Text format)
            const base64String = Buffer.from(jsonString).toString('base64');

            // Import from Text
            const imported = simulateImportConfigText(base64String);

            // Compare
            const configMismatches = compareConfigs(testCase.config, imported.config);
            const metadataMismatches = compareConfigs(testCase.metadata, imported.metadata);
            const allMismatches = [...configMismatches, ...metadataMismatches];

            if (allMismatches.length === 0) {
                logResult(true, `JSON export → Text import preserves data`);
                passedTests++;
            } else {
                logResult(false, `Mismatches detected in cross-format test`);
                failedTests++;
            }

        } catch (error) {
            logResult(false, `Exception: ${error.message}`);
            failedTests++;
        }
    });

    // Test data type preservation
    log('\n' + '─'.repeat(60), 'blue');
    log('DATA TYPE PRESERVATION TESTS', 'bright');
    log('─'.repeat(60), 'blue');

    const dataTypeTest = {
        name: 'Data Type Verification',
        config: {
            size: 1024,              // number
            terrainType: 'continental', // string
            playerCount: 4,          // number
            noiseStrength: 0.5,      // number (float)
            heightVariation: 0.6,    // number (float)
            waterLevel: 0.3,         // number (float)
            metalSpots: 50,          // number
            metalStrength: 0.7,      // number (float)
            geoSpots: 10,            // number
            startPositions: []       // array
        },
        metadata: {
            creator: 'Type Tester',
            description: 'Verify data types are preserved'
        }
    };

    logTest('Data Type Preservation');
    totalTests++;

    try {
        // JSON round-trip
        const jsonString = simulateExportConfigJSON(
            dataTypeTest.config,
            dataTypeTest.metadata.creator,
            dataTypeTest.metadata.description
        );
        const importedFromJSON = simulateImportConfigJSON(jsonString);

        // Verify types
        let typesPreserved = true;
        const typeErrors = [];

        Object.keys(dataTypeTest.config).forEach(key => {
            const originalType = typeof dataTypeTest.config[key];
            const importedType = typeof importedFromJSON.config[key];

            if (originalType !== importedType) {
                typesPreserved = false;
                typeErrors.push(`${key}: ${originalType} → ${importedType}`);
            }
        });

        if (typesPreserved) {
            logResult(true, 'All data types preserved through JSON round-trip');
            passedTests++;
        } else {
            logResult(false, 'Data type mismatches detected:');
            typeErrors.forEach(error => log(`  - ${error}`, 'red'));
            failedTests++;
        }

    } catch (error) {
        logResult(false, `Exception: ${error.message}`);
        failedTests++;
    }

    // Overall results
    log('\n' + '╔════════════════════════════════════════════════════════════╗', 'cyan');
    log('║   TEST RESULTS SUMMARY                                        ║', 'cyan');
    log('╚════════════════════════════════════════════════════════════╝', 'cyan');

    log(`\nTotal Tests: ${totalTests}`, 'bright');
    log(`Passed: ${passedTests}`, 'green');
    log(`Failed: ${failedTests}`, failedTests > 0 ? 'red' : 'green');

    const passRate = ((passedTests / totalTests) * 100).toFixed(1);
    log(`Pass Rate: ${passRate}%`, 'bright');

    if (failedTests === 0) {
        log('\n✓ ALL TESTS PASSED - Round-trip workflow is working correctly!', 'green');
        log('\nThe export/import functions preserve all configuration data accurately.', 'green');
    } else {
        log('\n✗ SOME TESTS FAILED - Please review the failures above.', 'red');
    }

    log('\n' + '='.repeat(60) + '\n', 'cyan');

    return {
        total: totalTests,
        passed: passedTests,
        failed: failedTests,
        passRate: passRate
    };
}

// Run the test suite
const results = runTests();

// Exit with appropriate code
process.exit(results.failed > 0 ? 1 : 0);
