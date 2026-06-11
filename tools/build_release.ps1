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
    Compress-Archive -LiteralPath $PayloadRoot -DestinationPath $ZipPath -CompressionLevel Optimal
} finally {
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
}

Write-Host "Release ZIP created: $ZipPath"

