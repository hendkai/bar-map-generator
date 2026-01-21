#!/usr/bin/env node

/**
 * Automated Test for Configuration Sharing Functionality
 *
 * This script tests the configuration import/export functionality
 * by simulating the key operations without requiring a browser.
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
    bold: '\x1b[1m'
};

// Test configuration
const testConfig = {
    size: 20,
    terrainType: 'continental',
    playerCount: 4,
    seed: 12345,
    waterLevel: 0.4,
    mountainHeight: 0.7,
    noiseScale: 1.5,
    erosion: 0.3,
    vegetation: 0.6,
    resourceDensity: 0.5
};

const testMetadata = {
    creator: 'Test User',
    description: 'Test configuration for sharing workflow'
};

// Helper functions (ported from bar_map_generator.html)
function exportConfigText(config, metadata) {
    const exportData = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        metadata: metadata,
        config: { ...config }
    };

    const jsonString = JSON.stringify(exportData);
    const base64String = Buffer.from(jsonString).toString('base64');
    return base64String;
}

function importConfigFromText(base64String) {
    const jsonString = Buffer.from(base64String, 'base64').toString('utf-8');
    const importData = JSON.parse(jsonString);
    return importData;
}

function validateConfigurationValues(config) {
    const errors = [];

    // Validate required fields
    if (config.size === undefined || typeof config.size !== 'number') {
        errors.push('size must be a number');
    }
    if (config.terrainType === undefined || typeof config.terrainType !== 'string') {
        errors.push('terrainType must be a string');
    }
    if (config.playerCount === undefined || typeof config.playerCount !== 'number') {
        errors.push('playerCount must be a number');
    }

    return errors;
}

// Test functions
function testExportConfiguration() {
    console.log(`\n${colors.cyan}${colors.bold}TEST 1: Export Configuration${colors.reset}`);

    try {
        const exported = exportConfigText(testConfig, testMetadata);

        console.log(`${colors.green}✓ Export successful${colors.reset}`);
        console.log(`  Exported string length: ${exported.length} characters`);
        console.log(`  First 50 chars: ${exported.substring(0, 50)}...`);

        return exported;
    } catch (error) {
        console.log(`${colors.red}✗ Export failed: ${error.message}${colors.reset}`);
        return null;
    }
}

function testImportConfiguration(exportedString) {
    console.log(`\n${colors.cyan}${colors.bold}TEST 2: Import Configuration${colors.reset}`);

    try {
        const imported = importConfigFromText(exportedString);

        console.log(`${colors.green}✓ Import successful${colors.reset}`);
        console.log(`  Version: ${imported.version}`);
        console.log(`  Timestamp: ${imported.timestamp}`);
        console.log(`  Has metadata: ${!!imported.metadata}`);
        console.log(`  Has config: ${!!imported.config}`);

        return imported;
    } catch (error) {
        console.log(`${colors.red}✗ Import failed: ${error.message}${colors.reset}`);
        return null;
    }
}

function testValidation(importedData) {
    console.log(`\n${colors.cyan}${colors.bold}TEST 3: Validate Configuration${colors.reset}`);

    try {
        const errors = validateConfigurationValues(importedData.config);

        if (errors.length > 0) {
            console.log(`${colors.red}✗ Validation failed:${colors.reset}`);
            errors.forEach(err => console.log(`  - ${err}`));
            return false;
        }

        console.log(`${colors.green}✓ Validation passed${colors.reset}`);
        return true;
    } catch (error) {
        console.log(`${colors.red}✗ Validation error: ${error.message}${colors.reset}`);
        return false;
    }
}

function testRoundTripIntegrity(original, imported) {
    console.log(`\n${colors.cyan}${colors.bold}TEST 4: Round-Trip Data Integrity${colors.reset}`);

    const config = imported.config;
    const metadata = imported.metadata;
    let allPassed = true;

    // Check config fields
    console.log(`\n${colors.blue}Configuration Fields:${colors.reset}`);
    for (const key in original) {
        const match = original[key] === config[key];
        const symbol = match ? '✓' : '✗';
        const color = match ? colors.green : colors.red;

        console.log(`  ${color}${symbol} ${key}: ${original[key]} → ${config[key]}${colors.reset}`);

        if (!match) allPassed = false;
    }

    // Check metadata fields
    console.log(`\n${colors.blue}Metadata Fields:${colors.reset}`);
    for (const key in testMetadata) {
        const match = testMetadata[key] === metadata[key];
        const symbol = match ? '✓' : '✗';
        const color = match ? colors.green : colors.red;

        console.log(`  ${color}${symbol} ${key}: ${testMetadata[key]} → ${metadata[key]}${colors.reset}`);

        if (!match) allPassed = false;
    }

    if (allPassed) {
        console.log(`\n${colors.green}✓ All fields preserved correctly${colors.reset}`);
    } else {
        console.log(`\n${colors.red}✗ Some fields were corrupted${colors.reset}`);
    }

    return allPassed;
}

function testSpecialCases() {
    console.log(`\n${colors.cyan}${colors.bold}TEST 5: Special Cases${colors.reset}`);

    let passed = 0;
    let total = 0;

    // Test 1: Empty metadata
    total++;
    try {
        const exported = exportConfigText(testConfig, {});
        const imported = importConfigFromText(exported);
        if (imported.metadata) {
            console.log(`${colors.green}✓ Empty metadata handled correctly${colors.reset}`);
            passed++;
        } else {
            console.log(`${colors.red}✗ Empty metadata not preserved${colors.reset}`);
        }
    } catch (error) {
        console.log(`${colors.red}✗ Empty metadata test failed: ${error.message}${colors.reset}`);
    }

    // Test 2: Special characters in metadata
    total++;
    try {
        const specialMetadata = {
            creator: 'Test User <script>alert("xss")</script>',
            description: 'Test with "quotes" and \'apostrophes\' and\nnewlines\ttabs'
        };
        const exported = exportConfigText(testConfig, specialMetadata);
        const imported = importConfigFromText(exported);

        if (imported.metadata.creator === specialMetadata.creator &&
            imported.metadata.description === specialMetadata.description) {
            console.log(`${colors.green}✓ Special characters preserved correctly${colors.reset}`);
            passed++;
        } else {
            console.log(`${colors.red}✗ Special characters corrupted${colors.reset}`);
        }
    } catch (error) {
        console.log(`${colors.red}✗ Special characters test failed: ${error.message}${colors.reset}`);
    }

    // Test 3: Extreme numeric values
    total++;
    try {
        const extremeConfig = {
            ...testConfig,
            size: 0,
            waterLevel: 1,
            mountainHeight: 0
        };
        const exported = exportConfigText(extremeConfig, testMetadata);
        const imported = importConfigFromText(exported);

        if (imported.config.size === 0 &&
            imported.config.waterLevel === 1 &&
            imported.config.mountainHeight === 0) {
            console.log(`${colors.green}✓ Extreme numeric values preserved${colors.reset}`);
            passed++;
        } else {
            console.log(`${colors.red}✗ Extreme numeric values corrupted${colors.reset}`);
        }
    } catch (error) {
        console.log(`${colors.red}✗ Extreme values test failed: ${error.message}${colors.reset}`);
    }

    console.log(`\nSpecial cases: ${passed}/${total} passed`);
    return passed === total;
}

function testBase64Encoding() {
    console.log(`\n${colors.cyan}${colors.bold}TEST 6: Base64 Encoding Validation${colors.reset}`);

    try {
        const exported = exportConfigText(testConfig, testMetadata);

        // Test 1: Valid base64 characters only
        const validBase64 = /^[A-Za-z0-9+/]+=*$/;
        const isValid = validBase64.test(exported);

        if (isValid) {
            console.log(`${colors.green}✓ Export uses valid base64 characters${colors.reset}`);
        } else {
            console.log(`${colors.red}✗ Export contains invalid characters${colors.reset}`);
            return false;
        }

        // Test 2: Proper padding
        const paddingCorrect = exported.length % 4 === 0;
        if (paddingCorrect) {
            console.log(`${colors.green}✓ Base64 padding is correct${colors.reset}`);
        } else {
            console.log(`${colors.red}✗ Base64 padding is incorrect${colors.reset}`);
            return false;
        }

        // Test 3: Can be decoded back
        try {
            const decoded = Buffer.from(exported, 'base64').toString('utf-8');
            const parsed = JSON.parse(decoded);
            console.log(`${colors.green}✓ Export can be decoded and parsed${colors.reset}`);
            return true;
        } catch (error) {
            console.log(`${colors.red}✗ Export cannot be decoded: ${error.message}${colors.reset}`);
            return false;
        }
    } catch (error) {
        console.log(`${colors.red}✗ Base64 encoding test failed: ${error.message}${colors.reset}`);
        return false;
    }
}

function generateTestReport(results) {
    console.log(`\n${colors.bold}${colors.blue}═══════════════════════════════════════${colors.reset}`);
    console.log(`${colors.bold}${colors.blue}     TEST REPORT SUMMARY${colors.reset}`);
    console.log(`${colors.bold}${colors.blue}═══════════════════════════════════════${colors.reset}\n`);

    const totalTests = results.length;
    const passedTests = results.filter(r => r.passed).length;
    const failedTests = totalTests - passedTests;

    console.log(`${colors.bold}Total Tests:${colors.reset} ${totalTests}`);
    console.log(`${colors.green}${colors.bold}Passed:${colors.reset} ${passedTests}`);
    console.log(`${colors.red}${colors.bold}Failed:${colors.reset} ${failedTests}`);
    console.log(`${colors.bold}Success Rate:${colors.reset} ${((passedTests / totalTests) * 100).toFixed(1)}%\n`);

    results.forEach((result, index) => {
        const status = result.passed ? `${colors.green}✓ PASS${colors.reset}` : `${colors.red}✗ FAIL${colors.reset}`;
        console.log(`${index + 1}. ${result.name}: ${status}`);
    });

    console.log(`\n${colors.bold}${colors.blue}═══════════════════════════════════════${colors.reset}`);

    // Save report to file
    const reportData = {
        timestamp: new Date().toISOString(),
        totalTests,
        passedTests,
        failedTests,
        successRate: ((passedTests / totalTests) * 100).toFixed(1) + '%',
        results: results
    };

    fs.writeFileSync(
        path.join(__dirname, 'test_results_config_sharing.json'),
        JSON.stringify(reportData, null, 2)
    );

    console.log(`\n${colors.cyan}📄 Test report saved to: test_results_config_sharing.json${colors.reset}`);

    return passedTests === totalTests;
}

// Main test execution
function runTests() {
    console.log(`${colors.bold}${colors.blue}
╔═══════════════════════════════════════╗
║   Configuration Sharing Test Suite   ║
║   Automated Testing for Subtask 3-2  ║
╚═══════════════════════════════════════╝
${colors.reset}`);

    console.log(`${colors.yellow}Testing configuration import/export functionality...${colors.reset}\n`);

    const results = [];

    // Test 1: Export
    const exported = testExportConfiguration();
    results.push({
        name: 'Export Configuration',
        passed: exported !== null
    });

    if (!exported) {
        console.log(`\n${colors.red}Cannot continue tests without successful export${colors.reset}`);
        process.exit(1);
    }

    // Test 2: Import
    const imported = testImportConfiguration(exported);
    results.push({
        name: 'Import Configuration',
        passed: imported !== null
    });

    if (!imported) {
        console.log(`\n${colors.red}Cannot continue tests without successful import${colors.reset}`);
        process.exit(1);
    }

    // Test 3: Validation
    const validationPassed = testValidation(imported);
    results.push({
        name: 'Validate Configuration Values',
        passed: validationPassed
    });

    // Test 4: Round-trip integrity
    const integrityPassed = testRoundTripIntegrity(testConfig, imported);
    results.push({
        name: 'Round-Trip Data Integrity',
        passed: integrityPassed
    });

    // Test 5: Special cases
    const specialCasesPassed = testSpecialCases();
    results.push({
        name: 'Special Cases Handling',
        passed: specialCasesPassed
    });

    // Test 6: Base64 encoding
    const base64Passed = testBase64Encoding();
    results.push({
        name: 'Base64 Encoding Validation',
        passed: base64Passed
    });

    // Generate report
    const allPassed = generateTestReport(results);

    console.log(`\n${allPassed ? colors.green : colors.red}${colors.bold}
${allPassed ? '✓ ALL TESTS PASSED' : '✗ SOME TESTS FAILED'}
${colors.reset}\n`);

    process.exit(allPassed ? 0 : 1);
}

// Run the tests
if (require.main === module) {
    runTests();
}

module.exports = {
    exportConfigText,
    importConfigFromText,
    validateConfigurationValues
};
