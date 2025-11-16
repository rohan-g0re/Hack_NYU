# Phase 4 Test Runner Script
# Runs all Phase 4 tests and collects results

Write-Host "=== Phase 4 Testing Suite ===" -ForegroundColor Cyan
Write-Host ""

# Activate conda environment
Write-Host "Activating conda environment..." -ForegroundColor Yellow
conda activate hackathon

# Set environment variables for live provider tests
$env:RUN_LIVE_PROVIDER_TESTS = "true"
$env:LLM_PROVIDER = "openrouter"
$env:LLM_ENABLE_OPENROUTER = "true"

Write-Host ""
Write-Host "=== Test Suite 1: Mocked Integration Tests ===" -ForegroundColor Green
python -m pytest tests/integration/test_api_endpoints.py -v --tb=short -m "phase4" | Tee-Object -FilePath "test_results_mocked.txt"

Write-Host ""
Write-Host "=== Test Suite 2: OpenRouter Endpoints ===" -ForegroundColor Green
python -m pytest tests/integration/live_openrouter/test_phase4_openrouter_endpoints.py -v --tb=short -m "phase4 and requires_openrouter" | Tee-Object -FilePath "test_results_openrouter_endpoints.txt"

Write-Host ""
Write-Host "=== Test Suite 3: OpenRouter Streaming ===" -ForegroundColor Green
python -m pytest tests/integration/live_openrouter/test_phase4_openrouter_streaming.py -v --tb=short -m "phase4 and requires_openrouter" | Tee-Object -FilePath "test_results_openrouter_streaming.txt"

Write-Host ""
Write-Host "=== Test Suite 4: OpenRouter Performance ===" -ForegroundColor Green
python -m pytest tests/integration/live_openrouter/test_phase4_openrouter_perf.py -v --tb=short -m "phase4 and requires_openrouter and perf" | Tee-Object -FilePath "test_results_openrouter_perf.txt"

Write-Host ""
Write-Host "=== All tests completed ===" -ForegroundColor Cyan

