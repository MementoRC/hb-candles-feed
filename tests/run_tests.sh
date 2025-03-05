#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Define test categories
UNIT_TESTS="tests/unit/"
INTEGRATION_TESTS="tests/integration/"
E2E_TESTS="tests/e2e/"

# Function to run tests
run_tests() {
    local test_path=$1
    local category=$2
    
    echo -e "${YELLOW}Running $category tests...${NC}"
    
    /home/memento/ClaudeCode/candles-feed/bin/python -m pytest -xvs "$test_path" > "$category.log" 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $category tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ $category tests FAILED${NC}"
        echo -e "${YELLOW}See $category.log for details${NC}"
        return 1
    fi
}

# Banner
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}      CANDLES FEED TESTING SUITE         ${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# Run tests for each category
run_tests "$UNIT_TESTS" "unit"
UNIT_STATUS=$?

run_tests "$INTEGRATION_TESTS" "integration" 
INTEGRATION_STATUS=$?

# No need for separate refactored integration tests - they're part of regular integration tests

run_tests "$E2E_TESTS" "e2e"
E2E_STATUS=$?

# Summary
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}              TEST SUMMARY               ${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

if [ $UNIT_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Unit Tests: PASS${NC}"
else
    echo -e "${RED}✗ Unit Tests: FAIL${NC}"
fi

if [ $INTEGRATION_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Integration Tests: PASS${NC}"
else
    echo -e "${RED}✗ Integration Tests: FAIL${NC}"
fi

# Refactored tests are now part of the regular integration tests

if [ $E2E_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ E2E Tests: PASS${NC}"
else
    echo -e "${RED}✗ E2E Tests: FAIL${NC}"
fi

echo ""

# Overall status
if [ $UNIT_STATUS -eq 0 ] && [ $INTEGRATION_STATUS -eq 0 ] && [ $E2E_STATUS -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi