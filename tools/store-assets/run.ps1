param(
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$ArgsList = @()
if ($OutDir -ne "") {
    $ArgsList = @("--out", $OutDir)
}

Write-Host "Generating Media Screen thumbnails..."
& python (Join-Path $ScriptDir "media_screen_thumbnail.py") @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Generating Media Speaker thumbnails..."
& python (Join-Path $ScriptDir "media_speaker_thumbnail.py") @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All store thumbnails generated successfully."
