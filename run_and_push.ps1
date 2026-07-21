$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $RepoDir "logs"
$null = New-Item -ItemType Directory -Path $LogDir -Force
$LogFile = Join-Path $LogDir "run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log { param([string]$Msg) "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Msg" | Out-File -FilePath $LogFile -Append }

Set-Location -LiteralPath $RepoDir

Write-Log "Starting capture..."
$output = & python capture_live_price.py 2>&1
$exitCode = $LASTEXITCODE

foreach ($line in $output) {
    Write-Log $line
}

if ($exitCode -eq 0) {
    Write-Log "Capture OK"

    & git config user.name "github-actions"
    & git config user.email "github-actions@github.com"

    $remote = "https://github.com/Eddy-Pos/pos-outlet-scraper.git"
    if ($env:GIT_PAT) {
        $remote = "https://x-access-token:$($env:GIT_PAT)@github.com/Eddy-Pos/pos-outlet-scraper.git"
    }
    & git remote set-url origin $remote

    & git add -A
    $diffOut = & git diff --quiet 2>&1
    $diffStagedOut = & git diff --staged --quiet 2>&1
    $hasChanges = $LASTEXITCODE -ne 0 -or (-not $?)
    if ($hasChanges) {
        $price = ($output | Out-String) -replace '(?s).*Buy RM ([\d.]+).*', '$1'
        $msg = "Gold price update: RM ${price}/g ($(Get-Date -Format 'yyyy-MM-dd HH:mm UTC'))"
        Write-Log "Committing: $msg"
        & git commit -m $msg 2>&1 | Out-File -FilePath $LogFile -Append
        & git pull --rebase 2>&1 | Out-File -FilePath $LogFile -Append
        & git push 2>&1 | Out-File -FilePath $LogFile -Append
        Write-Log "Push complete"
    } else {
        Write-Log "No changes to commit"
    }
    exit 0
} else {
    Write-Log "Capture FAILED, exit=$exitCode"
    exit $exitCode
}
