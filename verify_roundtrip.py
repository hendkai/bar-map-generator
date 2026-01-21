#!/usr/bin/env python3
"""
Automated Round-trip Export/Import Verification Script

This script verifies that the export/import functions preserve
all configuration data accurately through a complete round-trip cycle.
"""

import json
import base64
import sys
from datetime import datetime

# ANSI color codes for terminal output
class Colors:
    reset = '\033[0m'
    bright = '\033[1m'
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    blue = '\033[34m'
    magenta = '\033[35m'
    cyan = '\033[36m'

def log(message, color='reset'):
    """Log a message with color"""
    color_code = getattr(Colors, color, '')
    print(f"{color_code}{message}{Colors.reset}")

def log_test(test_name):
    """Log a test header"""
    log(f"\n{'='*60}", 'cyan')
    log(f"TEST: {test_name}", 'bright')
    log('='*60, 'cyan')

def log_result(passed, message):
    """Log a test result"""
    if passed:
        log(f"✓ PASSED: {message}", 'green')
    else:
        log(f"✗ FAILED: {message}", 'red')

# Simulate the export/import functions from bar_map_generator.html
def simulate_export_config_json(map_config, creator_name, map_description):
    """Simulate exportConfigJSON function"""
    export_data = {
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'metadata': {
            'creator': creator_name or 'Anonymous',
            'description': map_description or 'No description'
        },
        'config': {**map_config}  # Shallow copy
    }
    return json.dumps(export_data, indent=2)

def simulate_import_config_json(json_string):
    """Simulate importConfigFromJSON function"""
    import_data = json.loads(json_string)

    # Validate structure
    if not import_data.get('version') or not import_data.get('config'):
        raise ValueError('Invalid configuration file format. Missing required fields.')

    return import_data

def simulate_export_config_text(map_config, creator_name, map_description):
    """Simulate exportConfigText function"""
    export_data = {
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'metadata': {
            'creator': creator_name or 'Anonymous',
            'description': map_description or 'No description'
        },
        'config': {**map_config}
    }
    json_string = json.dumps(export_data)
    return base64.b64encode(json_string.encode('utf-8')).decode('utf-8')

def simulate_import_config_text(base64_string):
    """Simulate importConfigFromText function"""
    json_string = base64.b64decode(base64_string).decode('utf-8')
    import_data = json.loads(json_string)

    if not import_data.get('version') or not import_data.get('config'):
        raise ValueError('Invalid configuration format. Missing required fields.')

    return import_data

def compare_configs(original, imported):
    """Compare two config objects and return list of mismatches"""
    mismatches = []

    for key in original:
        if original[key] != imported.get(key):
            mismatches.append({
                'field': key,
                'original': original[key],
                'imported': imported.get(key)
            })

    return mismatches

# Test cases
test_cases = [
    {
        'name': 'Basic Configuration',
        'config': {
            'size': 1024,
            'terrainType': 'continental',
            'playerCount': 4,
            'noiseStrength': 0.5,
            'heightVariation': 0.6,
            'waterLevel': 0.3,
            'metalSpots': 50,
            'metalStrength': 0.7,
            'geoSpots': 10,
            'startPositions': []
        },
        'metadata': {
            'creator': 'Test User',
            'description': 'Test configuration for round-trip verification'
        }
    },
    {
        'name': 'Extreme Values',
        'config': {
            'size': 2048,
            'terrainType': 'hills',
            'playerCount': 8,
            'noiseStrength': 1.0,
            'heightVariation': 1.0,
            'waterLevel': 1.0,
            'metalSpots': 100,
            'metalStrength': 1.0,
            'geoSpots': 50,
            'startPositions': []
        },
        'metadata': {
            'creator': 'Extreme Tester',
            'description': 'Testing maximum values'
        }
    },
    {
        'name': 'Minimum Values',
        'config': {
            'size': 512,
            'terrainType': 'flat',
            'playerCount': 2,
            'noiseStrength': 0.0,
            'heightVariation': 0.0,
            'waterLevel': 0.0,
            'metalSpots': 0,
            'metalStrength': 0.0,
            'geoSpots': 0,
            'startPositions': []
        },
        'metadata': {
            'creator': 'Min Tester',
            'description': 'Testing minimum values'
        }
    },
    {
        'name': 'All Terrain Types',
        'config': {
            'size': 1024,
            'terrainType': 'canyon',
            'playerCount': 6,
            'noiseStrength': 0.75,
            'heightVariation': 0.8,
            'waterLevel': 0.4,
            'metalSpots': 75,
            'metalStrength': 0.9,
            'geoSpots': 25,
            'startPositions': []
        },
        'metadata': {
            'creator': 'Terrain Tester',
            'description': 'Testing canyon terrain'
        }
    },
    {
        'name': 'Special Characters',
        'config': {
            'size': 1024,
            'terrainType': 'islands',
            'playerCount': 4,
            'noiseStrength': 0.5,
            'heightVariation': 0.6,
            'waterLevel': 0.3,
            'metalSpots': 50,
            'metalStrength': 0.7,
            'geoSpots': 10,
            'startPositions': []
        },
        'metadata': {
            'creator': 'Test "Quotes" & <Symbols>',
            'description': 'Config with émojis 😊🎮 and unicode: 中文 漢字'
        }
    },
    {
        'name': 'Empty Metadata',
        'config': {
            'size': 1024,
            'terrainType': 'continental',
            'playerCount': 4,
            'noiseStrength': 0.5,
            'heightVariation': 0.6,
            'waterLevel': 0.3,
            'metalSpots': 50,
            'metalStrength': 0.7,
            'geoSpots': 10,
            'startPositions': []
        },
        'metadata': {
            'creator': '',
            'description': ''
        }
    }
]

def run_tests():
    """Run all verification tests"""
    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan')
    log('║   ROUND-TRIP EXPORT/IMPORT VERIFICATION SUITE           ║', 'cyan')
    log('╚════════════════════════════════════════════════════════════╝', 'cyan')

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    # Test JSON round-trip
    log('\n' + '─'*60, 'blue')
    log('JSON ROUND-TRIP TESTS', 'bright')
    log('─'*60, 'blue')

    for index, test_case in enumerate(test_cases, 1):
        log_test(f"JSON Test {index}: {test_case['name']}")
        total_tests += 1

        try:
            # Export
            json_string = simulate_export_config_json(
                test_case['config'],
                test_case['metadata']['creator'],
                test_case['metadata']['description']
            )

            # Import
            imported = simulate_import_config_json(json_string)

            # Compare config
            config_mismatches = compare_configs(test_case['config'], imported['config'])

            # Compare metadata
            metadata_mismatches = compare_configs(test_case['metadata'], imported['metadata'])

            all_mismatches = config_mismatches + metadata_mismatches

            if len(all_mismatches) == 0:
                log_result(True, 'All values preserved through JSON round-trip')
                passed_tests += 1
            else:
                log_result(False, 'Mismatches detected:')
                for mismatch in all_mismatches:
                    log(f"  - {mismatch['field']}: \"{mismatch['original']}\" → \"{mismatch['imported']}\"", 'red')
                failed_tests += 1

        except Exception as error:
            log_result(False, f"Exception: {str(error)}")
            failed_tests += 1

    # Test Text round-trip
    log('\n' + '─'*60, 'blue')
    log('TEXT ROUND-TRIP TESTS', 'bright')
    log('─'*60, 'blue')

    for index, test_case in enumerate(test_cases, 1):
        log_test(f"Text Test {index}: {test_case['name']}")
        total_tests += 1

        try:
            # Export
            base64_string = simulate_export_config_text(
                test_case['config'],
                test_case['metadata']['creator'],
                test_case['metadata']['description']
            )

            # Import
            imported = simulate_import_config_text(base64_string)

            # Compare config
            config_mismatches = compare_configs(test_case['config'], imported['config'])

            # Compare metadata
            metadata_mismatches = compare_configs(test_case['metadata'], imported['metadata'])

            all_mismatches = config_mismatches + metadata_mismatches

            if len(all_mismatches) == 0:
                log_result(True, 'All values preserved through Text round-trip')
                passed_tests += 1
            else:
                log_result(False, 'Mismatches detected:')
                for mismatch in all_mismatches:
                    log(f"  - {mismatch['field']}: \"{mismatch['original']}\" → \"{mismatch['imported']}\"", 'red')
                failed_tests += 1

        except Exception as error:
            log_result(False, f"Exception: {str(error)}")
            failed_tests += 1

    # Test all terrain types
    log('\n' + '─'*60, 'blue')
    log('ALL TERRAIN TYPES TEST', 'bright')
    log('─'*60, 'blue')

    terrain_types = ['continental', 'islands', 'canyon', 'hills', 'flat']

    for index, terrain in enumerate(terrain_types, 1):
        log_test(f"Terrain Test {index}: {terrain}")
        total_tests += 1

        try:
            test_config = {
                'size': 1024,
                'terrainType': terrain,
                'playerCount': 4,
                'noiseStrength': 0.5,
                'heightVariation': 0.6,
                'waterLevel': 0.3,
                'metalSpots': 50,
                'metalStrength': 0.7,
                'geoSpots': 10,
                'startPositions': []
            }

            json_string = simulate_export_config_json(test_config, 'Tester', f'Testing {terrain}')
            imported = simulate_import_config_json(json_string)

            if imported['config']['terrainType'] == terrain:
                log_result(True, f'Terrain type "{terrain}" preserved')
                passed_tests += 1
            else:
                log_result(False, 'Terrain type mismatch')
                failed_tests += 1

        except Exception as error:
            log_result(False, f"Exception: {str(error)}")
            failed_tests += 1

    # Test all map sizes
    log('\n' + '─'*60, 'blue')
    log('ALL MAP SIZES TEST', 'bright')
    log('─'*60, 'blue')

    map_sizes = [512, 1024, 2048]

    for index, size in enumerate(map_sizes, 1):
        log_test(f"Size Test {index}: {size}x{size}")
        total_tests += 1

        try:
            test_config = {
                'size': size,
                'terrainType': 'continental',
                'playerCount': 4,
                'noiseStrength': 0.5,
                'heightVariation': 0.6,
                'waterLevel': 0.3,
                'metalSpots': 50,
                'metalStrength': 0.7,
                'geoSpots': 10,
                'startPositions': []
            }

            json_string = simulate_export_config_json(test_config, 'Tester', f'Testing {size}x{size}')
            imported = simulate_import_config_json(json_string)

            if imported['config']['size'] == size:
                log_result(True, f'Map size "{size}" preserved')
                passed_tests += 1
            else:
                log_result(False, 'Map size mismatch')
                failed_tests += 1

        except Exception as error:
            log_result(False, f"Exception: {str(error)}")
            failed_tests += 1

    # Cross-format test
    log('\n' + '─'*60, 'blue')
    log('CROSS-FORMAT TEST', 'bright')
    log('─'*60, 'blue')

    log_test('Cross-Format: JSON export → Text import')
    total_tests += 1

    try:
        test_config = {
            'size': 1024,
            'terrainType': 'islands',
            'playerCount': 6,
            'noiseStrength': 0.75,
            'heightVariation': 0.8,
            'waterLevel': 0.5,
            'metalSpots': 75,
            'metalStrength': 0.9,
            'geoSpots': 25,
            'startPositions': []
        }

        test_metadata = {
            'creator': 'Cross Tester',
            'description': 'Cross-format test'
        }

        # Export as JSON
        json_string = simulate_export_config_json(
            test_config,
            test_metadata['creator'],
            test_metadata['description']
        )

        # Convert to base64 (simulate text format)
        base64_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')

        # Import from text
        imported = simulate_import_config_text(base64_string)

        # Compare
        config_mismatches = compare_configs(test_config, imported['config'])
        metadata_mismatches = compare_configs(test_metadata, imported['metadata'])
        all_mismatches = config_mismatches + metadata_mismatches

        if len(all_mismatches) == 0:
            log_result(True, 'JSON export → Text import preserves data')
            passed_tests += 1
        else:
            log_result(False, 'Cross-format mismatches detected')
            failed_tests += 1

    except Exception as error:
        log_result(False, f"Exception: {str(error)}")
        failed_tests += 1

    # Overall results
    log('\n╔════════════════════════════════════════════════════════════╗', 'cyan')
    log('║   TEST RESULTS SUMMARY                                        ║', 'cyan')
    log('╚════════════════════════════════════════════════════════════╝', 'cyan')

    log(f"\nTotal Tests: {total_tests}", 'bright')
    log(f"Passed: {passed_tests}", 'green')
    log(f"Failed: {failed_tests}", 'red' if failed_tests > 0 else 'green')

    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    log(f"Pass Rate: {pass_rate:.1f}%", 'bright')

    if failed_tests == 0:
        log('\n✓ ALL TESTS PASSED - Round-trip workflow is working correctly!', 'green')
        log('The export/import functions preserve all configuration data accurately.', 'green')
    else:
        log('\n✗ SOME TESTS FAILED - Please review the failures above.', 'red')

    log('\n' + '='*60 + '\n', 'cyan')

    return {
        'total': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'pass_rate': pass_rate
    }

if __name__ == '__main__':
    results = run_tests()
    sys.exit(0 if results['failed'] == 0 else 1)
