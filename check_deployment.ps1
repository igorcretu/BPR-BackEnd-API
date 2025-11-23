# Script to check if the ML model deployment is successful
# Run this periodically to check deployment status

Write-Host ""
Write-Host "Checking Deployment Status..." -ForegroundColor Cyan
Write-Host "============================================================"

# 1. Check GitHub Actions status
Write-Host "`n1️⃣ GitHub Actions Workflow:" -ForegroundColor Yellow
Write-Host "   Visit: https://github.com/igorcretu/BPR-BackEnd-API/actions"
Write-Host "   Look for the workflow run triggered by commit ce6daa9"

# 2. Check production health endpoint
Write-Host "`n2️⃣ Production Health Check:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method GET -ErrorAction Stop
    
    Write-Host "   Status: $($response.status)" -ForegroundColor $(if ($response.status -eq "healthy") { "Green" } else { "Red" })
    Write-Host "   ML Model Info:" -ForegroundColor Cyan
    Write-Host "     - Loaded: $($response.ml_model.loaded)" -ForegroundColor $(if ($response.ml_model.loaded) { "Green" } else { "Red" })
    Write-Host "     - Type: $($response.ml_model.type)"
    Write-Host "     - Model Name: $($response.ml_model.model_name)"
    Write-Host "     - Version: $($response.ml_model.version)"
    Write-Host "     - Test R2: $($response.ml_model.test_r2)"
    Write-Host "     - Test MAE: $($response.ml_model.test_mae)"
    Write-Host "     - Features: $($response.ml_model.features_count)"
    
    if ($response.ml_model.loaded -eq $true) {
        Write-Host "`n✅ SUCCESS! ML Model is now loaded in production!" -ForegroundColor Green
    } else {
        Write-Host "`n⏳ Model not yet loaded. Deployment may still be in progress..." -ForegroundColor Yellow
        Write-Host "   Possible reasons:" -ForegroundColor Gray
        Write-Host "   - GitHub Actions workflow still running (building Docker image)" -ForegroundColor Gray
        Write-Host "   - Docker image not yet pulled on Raspberry Pi" -ForegroundColor Gray
        Write-Host "   - Container restart pending" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Failed to connect to production server" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Check latest commit
Write-Host "`n3️⃣ Latest Backend Commit:" -ForegroundColor Yellow
Push-Location "c:\Users\Igor Cretu\Desktop\Bachelor\Project\BackEnd\API"
$latestCommit = git log -1 --oneline
Write-Host "   $latestCommit"
Pop-Location

# 4. Deployment timeline estimate
Write-Host "`n4️⃣ Deployment Timeline (estimated):" -ForegroundColor Yellow
Write-Host "   - Test phase: ~2-3 minutes"
Write-Host "   - Docker build (ARM64): ~5-8 minutes"
Write-Host "   - Push to registry: ~1-2 minutes"
Write-Host "   - Deploy to Pi: ~2-3 minutes"
Write-Host "   - Total: ~10-15 minutes"

Write-Host ""
Write-Host "============================================================"
Write-Host "Tip: Run this script every few minutes to check progress" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host ""
