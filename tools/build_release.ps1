param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectName = "backbone_state_tracker"
$ParentDir = Split-Path $ProjectRoot -Parent
$DistDir = Join-Path $ProjectRoot "dist"
$VersionFile = Join-Path $ProjectRoot "core\version.py"

$versionText = Get-Content -LiteralPath $VersionFile -Raw
if ($versionText -notmatch 'APP_VERSION\s*=\s*"([^"]+)"') {
    throw "Unable to read APP_VERSION from $VersionFile"
}
$Version = $Matches[1]
$DateStamp = Get-Date -Format "yyyyMMdd"
$ZipName = "${ProjectName}_v${Version}_${DateStamp}_source.zip"
$ZipPath = Join-Path $DistDir $ZipName

function Invoke-Validation {
    $previousPythonPath = $env:PYTHONPATH
    try {
        if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
            $env:PYTHONPATH = $ParentDir
        } else {
            $env:PYTHONPATH = "$ParentDir;$previousPythonPath"
        }
        $env:PYTHONDONTWRITEBYTECODE = "1"
        Push-Location $ProjectRoot
        try {
            python -m unittest discover -s tests
            python -c "from backbone_state_tracker.core.gui import BackboneStateTrackerApp; app=BackboneStateTrackerApp(); app.update(); print(app.title()); app.destroy()"
        } finally {
            Pop-Location
        }
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }
}

function Test-ExcludedPath {
    param(
        [string]$RelativePath,
        [bool]$IsDirectory
    )

    $normalized = $RelativePath.Replace("/", "\")
    $parts = $normalized -split "\\"

    foreach ($part in $parts) {
        if ($part -in @(".git", "outputs", "dist", "build", "__pycache__", ".venv", "venv", ".pytest_cache")) {
            return $true
        }
    }

    if (-not $IsDirectory -and $normalized -eq "config\devices.yaml") {
        return $true
    }

    if (-not $IsDirectory -and $normalized -like "*.pyc") {
        return $true
    }

    if (-not $IsDirectory -and $normalized -like "*.spec") {
        return $true
    }

    return $false
}

function Copy-ReleaseTree {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot
    )

    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
    $sourceRootWithSep = $SourceRoot.TrimEnd("\") + "\"
    Get-ChildItem -LiteralPath $SourceRoot -Force -Recurse | ForEach-Object {
        $relative = $_.FullName.Substring($sourceRootWithSep.Length)
        if (Test-ExcludedPath -RelativePath $relative -IsDirectory $_.PSIsContainer) {
            return
        }

        $destination = Join-Path $DestinationRoot $relative
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $destination | Out-Null
        } else {
            $destinationParent = Split-Path $destination -Parent
            New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
        }
    }
}

if (-not $SkipTests) {
    Invoke-Validation
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

$StagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("${ProjectName}_release_" + [guid]::NewGuid().ToString("N"))
$PayloadRoot = Join-Path $StagingRoot $ProjectName

try {
    Copy-ReleaseTree -SourceRoot $ProjectRoot -DestinationRoot $PayloadRoot
    $packageInfoText = @"
Backbone State Tracker v$Version
Package type: Source ZIP
Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")

Contents:
- Source code
- Config examples
- Operator and developer guides
- Unit tests
- Release packaging scripts

Excluded:
- .git
- outputs
- dist
- build
- config\devices.yaml
- Python caches and virtual environments

Verification:
- Compare this ZIP file SHA256 with the matching .sha256.txt file in dist.
- A version-level release_manifest.txt file is also generated in dist.
"@
    Set-Content -LiteralPath (Join-Path $PayloadRoot "PACKAGE_INFO.txt") -Value $packageInfoText -Encoding UTF8
    Compress-Archive -LiteralPath $PayloadRoot -DestinationPath $ZipPath -CompressionLevel Optimal
} finally {
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
}

$ManifestTool = Join-Path $ProjectRoot "tools\write_release_manifest.py"
python $ManifestTool --project-name $ProjectName --version $Version --date-stamp $DateStamp --dist-dir $DistDir --package $ZipPath
if ($LASTEXITCODE -ne 0) {
    throw "Release manifest generation failed with exit code $LASTEXITCODE"
}

$VerifierTool = Join-Path $ProjectRoot "tools\verify_release_package.py"
python $VerifierTool $ZipPath --type source --require-manifest
if ($LASTEXITCODE -ne 0) {
    throw "Release package verification failed with exit code $LASTEXITCODE"
}

$PowerShellVerifierSource = Join-Path $ProjectRoot "tools\verify_release_package.ps1"
$PowerShellVerifierTarget = Join-Path $DistDir "${ProjectName}_v${Version}_${DateStamp}_verify_release_package.ps1"
Copy-Item -LiteralPath $PowerShellVerifierSource -Destination $PowerShellVerifierTarget -Force

Write-Host "Release ZIP created: $ZipPath"

