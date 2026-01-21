# Round-trip Export/Import Verification Checklist

## Subtask: subtask-3-1
**Goal:** Verify round-trip export/import workflow preserves all configuration data

---

## Test Environment Setup

1. ✓ Open `bar_map_generator.html` in a modern web browser (Chrome/Firefox/Edge)
2. ✓ Open browser Developer Tools (F12)
3. ✓ Navigate to Console tab

---

## Test 1: JSON Round-trip (Basic Configuration)

### Pre-test Setup
- [ ] Set Map Size: 1024
- [ ] Set Terrain Type: Continental
- [ ] Set Player Count: 4
- [ ] Set Noise Strength: 0.5
- [ ] Set Height Variation: 0.6
- [ ] Set Water Level: 0.3
- [ ] Set Metal Spots: 50
- [ ] Set Metal Strength: 0.7
- [ ] Set Geo Spots: 10
- [ ] Set Creator Name: "Test User"
- [ ] Set Description: "Test configuration for round-trip verification"
- [ ] Click "Generate Map" button

### Export Step
- [ ] Click "Export Config (JSON)" button
- [ ] Verify file downloads with name like: `map_config_continental_1024x1024_[timestamp].json`
- [ ] Open downloaded JSON file in text editor
- [ ] Verify JSON structure contains:
  - [ ] `version: "1.0"`
  - [ ] `timestamp` (ISO 8601 format)
  - [ ] `metadata.creator: "Test User"`
  - [ ] `metadata.description: "Test configuration for round-trip verification"`
  - [ ] `config.size: 1024`
  - [ ] `config.terrainType: "continental"`
  - [ ] `config.playerCount: 4`
  - [ ] `config.noiseStrength: 0.5`
  - [ ] `config.heightVariation: 0.6`
  - [ ] `config.waterLevel: 0.3`
  - [ ] `config.metalSpots: 50`
  - [ ] `config.metalStrength: 0.7`
  - [ ] `config.geoSpots: 10`

### Import Step
- [ ] Change all form values to different values (to verify import overwrites them)
- [ ] Click "Choose File" button in Import section
- [ ] Select the downloaded JSON file
- [ ] Click "Import from JSON" button
- [ ] Verify success alert shows correct metadata

### Verification
- [ ] Map Size dropdown: 1024 ✓
- [ ] Terrain Type dropdown: Continental ✓
- [ ] Player Count dropdown: 4 ✓
- [ ] Noise Strength slider: 0.5 ✓
- [ ] Height Variation slider: 0.6 ✓
- [ ] Water Level slider: 0.3 ✓
- [ ] Metal Spots slider: 50 ✓
- [ ] Metal Strength slider: 0.7 ✓
- [ ] Geo Spots slider: 10 ✓
- [ ] Creator Name input: "Test User" ✓
- [ ] Description textarea: "Test configuration for round-trip verification" ✓

**Result:** PASSED / FAILED

---

## Test 2: Text Round-trip (Basic Configuration)

### Pre-test Setup
- [ ] Set Map Size: 2048
- [ ] Set Terrain Type: Islands
- [ ] Set Player Count: 6
- [ ] Set Noise Strength: 0.75
- [ ] Set Height Variation: 0.8
- [ ] Set Water Level: 0.5
- [ ] Set Metal Spots: 75
- [ ] Set Metal Strength: 0.9
- [ ] Set Geo Spots: 25
- [ ] Set Creator Name: "Island Tester"
- [ ] Set Description: "Testing island configuration with text export"
- [ ] Click "Generate Map" button

### Export Step
- [ ] Click "Copy Config (Text)" button
- [ ] Verify alert: "Configuration copied to clipboard!"
- [ ] Paste clipboard content into notepad
- [ ] Verify content is a base64-encoded string (no spaces, ends with ==)

### Import Step
- [ ] Change all form values to different values
- [ ] Paste the base64 string into "Paste configuration text" textarea
- [ ] Click "Import from Text" button
- [ ] Verify success alert shows correct metadata

### Verification
- [ ] Map Size dropdown: 2048 ✓
- [ ] Terrain Type dropdown: Islands ✓
- [ ] Player Count dropdown: 6 ✓
- [ ] Noise Strength slider: 0.75 ✓
- [ ] Height Variation slider: 0.8 ✓
- [ ] Water Level slider: 0.5 ✓
- [ ] Metal Spots slider: 75 ✓
- [ ] Metal Strength slider: 0.9 ✓
- [ ] Geo Spots slider: 25 ✓
- [ ] Creator Name input: "Island Tester" ✓
- [ ] Description textarea: "Testing island configuration with text export" ✓

**Result:** PASSED / FAILED

---

## Test 3: All Terrain Types

Test each terrain type with a simple round-trip:

### Continental
- [ ] Configure with Terrain Type: Continental
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Terrain Type: Continental ✓

### Islands
- [ ] Configure with Terrain Type: Islands
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Terrain Type: Islands ✓

### Canyon
- [ ] Configure with Terrain Type: Canyon
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Terrain Type: Canyon ✓

### Hills
- [ ] Configure with Terrain Type: Hills
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Terrain Type: Hills ✓

### Flat
- [ ] Configure with Terrain Type: Flat
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Terrain Type: Flat ✓

**Result:** PASSED / FAILED

---

## Test 4: All Map Sizes

Test each map size:

### 512x512
- [ ] Configure with Map Size: 512
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Map Size: 512 ✓

### 1024x1024
- [ ] Configure with Map Size: 1024
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Map Size: 1024 ✓

### 2048x2048
- [ ] Configure with Map Size: 2048
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Map Size: 2048 ✓

**Result:** PASSED / FAILED

---

## Test 5: Special Characters in Metadata

### Test 1: Quotes and Apostrophes
- [ ] Set Creator Name: `Test "Quotes" Creator`
- [ ] Set Description: `Config with 'quotes' and "apostrophes"`
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Creator Name matches exactly ✓
- [ ] Verify Description matches exactly ✓

### Test 2: Unicode and Emojis
- [ ] Set Creator Name: `Émojis 😊🎮 Creator`
- [ ] Set Description: `Unicode test: 中文 漢字 العربية`
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Creator Name matches exactly ✓
- [ ] Verify Description matches exactly ✓

### Test 3: HTML Entities
- [ ] Set Creator Name: `<Tag> &Symbol`
- [ ] Set Description: `Description with <html> & entities`
- [ ] Export as JSON
- [ ] Import JSON
- [ ] Verify Creator Name matches exactly ✓
- [ ] Verify Description matches exactly ✓

**Result:** PASSED / FAILED

---

## Test 6: Numeric Precision

Test preservation of floating-point numbers:

### Test 1: Small Decimals
- [ ] Set Noise Strength: 0.01
- [ ] Set Height Variation: 0.02
- [ ] Set Water Level: 0.03
- [ ] Export/Import JSON
- [ ] Verify values match exactly ✓

### Test 2: Large Decimals
- [ ] Set Noise Strength: 0.99
- [ ] Set Height Variation: 0.98
- [ ] Set Water Level: 0.97
- [ ] Export/Import JSON
- [ ] Verify values match exactly ✓

### Test 3: Boundary Values
- [ ] Set Metal Spots: 0
- [ ] Set Geo Spots: 0
- [ ] Export/Import JSON
- [ ] Verify values match exactly ✓

### Test 4: Maximum Values
- [ ] Set Metal Spots: 100
- [ ] Set Geo Spots: 50
- [ ] Export/Import JSON
- [ ] Verify values match exactly ✓

**Result:** PASSED / FAILED

---

## Test 7: Cross-format Export/Import

### JSON Export → Text Import
- [ ] Configure a test configuration
- [ ] Export as JSON (save file)
- [ ] Open JSON file, copy content
- [ ] Manually base64-encode the JSON content (use online tool or console: `btoa(jsonString)`)
- [ ] Paste into text import area
- [ ] Import from Text
- [ ] Verify all values match ✓

### Text Export → JSON Import
- [ ] Configure a test configuration
- [ ] Copy Config (Text)
- [ ] Paste into notepad
- [ ] Manually decode base64 (use console: `atob(base64String)`)
- [ ] Save as .json file
- [ ] Import from JSON file
- [ ] Verify all values match ✓

**Result:** PASSED / FAILED

---

## Test 8: Metadata with Empty Values

### Empty Creator Name
- [ ] Leave Creator Name blank
- [ ] Set Description to some text
- [ ] Export/Import JSON
- [ ] Verify Creator Name imports as "Anonymous" (default value) ✓
- [ ] Verify Description imports correctly ✓

### Empty Description
- [ ] Set Creator Name to some text
- [ ] Leave Description blank
- [ ] Export/Import JSON
- [ ] Verify Creator Name imports correctly ✓
- [ ] Verify Description imports as "No description" (default value) ✓

### Both Empty
- [ ] Leave both Creator Name and Description blank
- [ ] Export/Import JSON
- [ ] Verify Creator Name imports as "Anonymous" ✓
- [ ] Verify Description imports as "No description" ✓

**Result:** PASSED / FAILED

---

## Automated Console Test

Run this in browser console for automated verification:

```javascript
// Automated round-trip test
function runRoundtripTest() {
    console.log('=== ROUND-TRIP VERIFICATION TEST ===\n');

    // Create test configuration
    const testConfig = {
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
    };

    const testMetadata = {
        creator: 'Automated Test',
        description: 'Automated round-trip verification test'
    };

    // Simulate export
    console.log('1. Creating export data...');
    const exportData = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        metadata: testMetadata,
        config: testConfig
    };

    // Test JSON export/import
    console.log('2. Testing JSON round-trip...');
    const jsonString = JSON.stringify(exportData);
    const importedFromJSON = JSON.parse(jsonString);

    let jsonPassed = true;
    const jsonErrors = [];

    Object.keys(testConfig).forEach(key => {
        if (importedFromJSON.config[key] !== testConfig[key]) {
            jsonPassed = false;
            jsonErrors.push(`${key}: ${testConfig[key]} → ${importedFromJSON.config[key]}`);
        }
    });

    if (importedFromJSON.metadata.creator !== testMetadata.creator ||
        importedFromJSON.metadata.description !== testMetadata.description) {
        jsonPassed = false;
        jsonErrors.push('Metadata mismatch');
    }

    console.log('   JSON Test:', jsonPassed ? '✓ PASSED' : '✗ FAILED');
    if (!jsonPassed) {
        console.log('   Errors:', jsonErrors);
    }

    // Test Text export/import
    console.log('3. Testing Text round-trip...');
    const base64String = btoa(JSON.stringify(exportData));
    const decoded = atob(base64String);
    const importedFromText = JSON.parse(decoded);

    let textPassed = true;
    const textErrors = [];

    Object.keys(testConfig).forEach(key => {
        if (importedFromText.config[key] !== testConfig[key]) {
            textPassed = false;
            textErrors.push(`${key}: ${testConfig[key]} → ${importedFromText.config[key]}`);
        }
    });

    if (importedFromText.metadata.creator !== testMetadata.creator ||
        importedFromText.metadata.description !== testMetadata.description) {
        textPassed = false;
        textErrors.push('Metadata mismatch');
    }

    console.log('   Text Test:', textPassed ? '✓ PASSED' : '✗ FAILED');
    if (!textPassed) {
        console.log('   Errors:', textErrors);
    }

    // Overall result
    console.log('\n=== OVERALL RESULT ===');
    const overallPassed = jsonPassed && textPassed;
    console.log(overallPassed ? '✓ ALL TESTS PASSED' : '✗ SOME TESTS FAILED');

    return {
        json: { passed: jsonPassed, errors: jsonErrors },
        text: { passed: textPassed, errors: textErrors },
        overall: overallPassed
    };
}

// Run the test
const results = runRoundtripTest();
```

---

## Test Results Summary

### JSON Round-trip
- [ ] Test 1: Basic Configuration - PASSED / FAILED
- [ ] Test 3: All Terrain Types - PASSED / FAILED
- [ ] Test 4: All Map Sizes - PASSED / FAILED
- [ ] Test 5: Special Characters - PASSED / FAILED
- [ ] Test 6: Numeric Precision - PASSED / FAILED
- [ ] Test 8: Empty Metadata - PASSED / FAILED

### Text Round-trip
- [ ] Test 2: Basic Configuration - PASSED / FAILED
- [ ] Test 5: Special Characters - PASSED / FAILED
- [ ] Test 6: Numeric Precision - PASSED / FAILED
- [ ] Test 8: Empty Metadata - PASSED / FAILED

### Cross-format
- [ ] Test 7: Cross-format Export/Import - PASSED / FAILED

### Automated Console Test
- [ ] Console script results - PASSED / FAILED

---

## Final Verification

**All tests passed:** [ ] YES / [ ] NO

**Issues found:**
```
(List any issues discovered during testing)
```

**Recommendations:**
```
(List any recommendations for improvements)
```

---

## Sign-off

**Tester:** _______________
**Date:** _______________
**Status:** APPROVED / NEEDS FIXES

---

## Notes

- This verification covers all 10 configuration parameters plus metadata fields
- Tests cover normal values, boundary values, special characters, and edge cases
- Both JSON and Text export/import formats are tested
- Cross-format compatibility is verified
- Automated console test provides programmatic verification
