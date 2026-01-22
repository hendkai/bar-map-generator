# E2E Testing Suite

## Overview

This directory contains comprehensive end-to-end testing infrastructure for the Community Map Sharing Portal.

## Test Files

### 1. Automated API Testing
**File:** `e2e-test-workflow.sh`

Bash script that automates the complete end-to-end workflow using curl commands:

- User registration and authentication
- Map upload with metadata
- Map browsing and pagination
- Search and filtering
- Map detail retrieval
- Rating submission
- Comment submission
- Map download with count verification

**Usage:**
```bash
chmod +x e2e-test-workflow.sh
./tests/e2e-test-workflow.sh
```

**Requirements:**
- Backend server running on http://localhost:8000
- PostgreSQL database running and migrations applied
- `curl`, `jq`, and `zip` commands available

**Output:**
- Console output with colored test results
- Log file: `./test-results/e2e-results-<timestamp>.log`

### 2. Manual Testing Guide
**File:** `E2E-MANUAL-TEST-GUIDE.md`

Comprehensive step-by-step guide for manual browser-based testing covering:

- Test Scenario 1: Complete User Journey (Generate → Download)
- Test Scenario 2: User Authentication Flow
- Test Scenario 3: Rating and Comment System
- Test Scenario 4: Error Handling

Each scenario includes:
- Detailed step-by-step instructions
- Expected results for each step
- Checkboxes for actual results
- Test data recording templates
- Screenshots/notes sections

**Usage:**
```bash
# Open the guide
cat tests/E2E-MANUAL-TEST-GUIDE.md

# Or open in your preferred editor/markdown viewer
```

### 3. Code Review Validation
**File:** `E2E-CODE-REVIEW-VALIDATION.md`

Complete static code analysis validation document that verifies:

- All 9 integration points in the workflow
- Data flow between frontend and backend
- Error handling implementations
- Code quality metrics
- API endpoint specifications
- Database operations

**Key Sections:**
- Integration Point Verification (9 steps)
- Complete Workflow Trace
- Error Handling Validation
- Code Quality Verification
- Runtime Testing Instructions

**Status:** ✅ Code Review Complete - All integration points verified

### 4. Testing Overview (This File)

Quick reference guide for the testing suite.

## Test Infrastructure

### Directory Structure
```
tests/
├── README.md                          # This file
├── e2e-test-workflow.sh               # Automated test script
├── E2E-MANUAL-TEST-GUIDE.md           # Manual testing guide
├── E2E-CODE-REVIEW-VALIDATION.md      # Code review validation
└── test-results/                      # Test output logs (auto-created)
    └── e2e-results-<timestamp>.log    # Individual test run logs
```

## Test Coverage

### Complete Workflow (9 Integration Points)

1. **Generate → Share Button**
   - Map metadata capture from generator
   - Preview image capture from canvas
   - localStorage integration
   - Community portal navigation

2. **Share → Upload Form Pre-fill**
   - Metadata retrieval from localStorage
   - Form field auto-population
   - Preview image conversion and display
   - Intelligent name/description generation

3. **Upload → Backend API**
   - Authentication validation
   - Form validation (required fields, file types)
   - Multipart file upload
   - Database record creation
   - File storage (map + preview)

4. **Browse → Maps List**
   - Paginated API requests
   - Filter and search parameters
   - Map grid display
   - Pagination controls

5. **Search → Filter Integration**
   - Filter control event listeners
   - Query parameter building
   - Debounced search input
   - Filter composition

6. **Map Detail → API**
   - GET request for map details
   - Complete metadata display
   - Preview image rendering
   - Download count display

7. **Rating → API**
   - Authentication requirement
   - POST request to submit rating
   - Create or update logic
   - Statistics recalculation
   - UI update with new rating

8. **Comment → API**
   - CRUD operations (Create, Read, Update, Delete)
   - Authentication requirements
   - Authorization (edit own comments only)
   - Comments thread display

9. **Download → Count Increment**
   - GET request for file download
   - Database transaction for count increment
   - File response with correct headers
   - Client-side blob download
   - UI refresh to show updated count

## Quick Start

### 1. Prerequisites

Start the backend server:
```bash
cd backend
# Option A: Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option B: Using Docker Compose
docker-compose up -d
```

Apply database migrations:
```bash
cd backend
alembic upgrade head
```

### 2. Run Automated Tests

```bash
# From project root
chmod +x tests/e2e-test-workflow.sh
./tests/e2e-test-workflow.sh
```

Expected output:
- Colored console output showing test progress
- Summary of passed/failed tests
- Detailed log file in `./test-results/`

### 3. Run Manual Tests

Open the manual test guide:
```bash
cat tests/E2E-MANUAL-TEST-GUIDE.md
```

Follow the step-by-step instructions in your browser.

### 4. Review Code Validation

Read the code review validation:
```bash
cat tests/E2E-CODE-REVIEW-VALIDATION.md
```

## Test Results Interpretation

### Automated Test Results

**Success Indicators:**
- All tests show `✓` marks
- Exit code 0 (no errors)
- Summary shows "Tests Passed: X, Tests Failed: 0"

**Failure Indicators:**
- Any tests show `✗` marks
- Exit code 1 (errors occurred)
- Check log file for detailed error messages

### Manual Test Results

Use the checkboxes in the guide to track:
- [ ] Each step completion
- [ ] Pass/Fail for expected results
- Document any deviations

## CI/CD Integration

The automated test script can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    chmod +x tests/e2e-test-workflow.sh
    ./tests/e2e-test-workflow.sh
  env:
    API_BASE_URL: http://localhost:8000
```

Exit codes:
- `0`: All tests passed
- `1`: One or more tests failed

## Troubleshooting

### Common Issues

**Server not running:**
```
ERROR: Backend server is not running
```
**Solution:** Start the backend server first (see Quick Start)

**Database connection failed:**
```
ERROR: Failed to connect to database
```
**Solution:** Check PostgreSQL is running and migrations applied

**Port already in use:**
```
ERROR: Address already in use
```
**Solution:** Kill process using port 8000 or change port in config

**Permission denied:**
```
bash: ./tests/e2e-test-workflow.sh: Permission denied
```
**Solution:** Run `chmod +x tests/e2e-test-workflow.sh`

## Contributing

When adding new features, update these test files:

1. **Add test cases** to `e2e-test-workflow.sh`
2. **Add manual test steps** to `E2E-MANUAL-TEST-GUIDE.md`
3. **Document integration** in `E2E-CODE-REVIEW-VALIDATION.md`

## Test Metrics

**Current Coverage:**
- Integration Points: 9/9 (100%)
- Error Categories: 9/9 (100%)
- Code Quality Metrics: 100% verified

**Test Types:**
- Automated API Tests: 9 test functions
- Manual Test Steps: 40+ steps across 4 scenarios
- Code Review Checks: 100+ verification points

## Support

For issues or questions:
1. Check the log files in `./test-results/`
2. Review the code validation document
3. Consult the implementation plan: `.auto-claude/specs/010-community-map-sharing-portal/implementation_plan.json`
4. Check build progress: `.auto-claude/specs/010-community-map-sharing-portal/build-progress.txt`

---

**Last Updated:** 2026-01-22
**Test Suite Version:** 1.0
**Status:** Code Review Complete, Runtime Testing Pending
