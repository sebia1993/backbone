param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectName = "backbone_state_tracker"
$ExeName = "BackboneStateTracker"
$ParentDir = Split-Path $ProjectRoot -Parent
$DistDir = Join-Path $ProjectRoot "dist"
$VersionFile = Join-Path $ProjectRoot "core\version.py"

$versionText = Get-Content -LiteralPath $VersionFile -Raw
if ($versionText -notmatch 'APP_VERSION\s*=\s*"([^"]+)"') {
    throw "Unable to read APP_VERSION from $VersionFile"
}
$Version = $Matches[1]
$DateStamp = Get-Date -Format "yyyyMMdd"
$ZipName = "${ProjectName}_v${Version}_${DateStamp}_windows_exe.zip"
$ZipPath = Join-Path $DistDir $ZipName

function Invoke-SourceValidation {
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
            python app.py --smoke-check
        } finally {
            Pop-Location
        }
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }
}

function Copy-DirectoryContent {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        return
    }

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        $target = Join-Path $Destination $_.Name
        if ($_.PSIsContainer) {
            Copy-DirectoryContent -Source $_.FullName -Destination $target
        } else {
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
        }
    }
}

if (-not $SkipTests) {
    Invoke-SourceValidation
}

python -m PyInstaller --version | Out-Null

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

$BuildRoot = Join-Path $ProjectRoot ("build\pyinstaller_" + [guid]::NewGuid().ToString("N"))
$PyInstallerDist = Join-Path $BuildRoot "dist"
$PyInstallerWork = Join-Path $BuildRoot "work"
$PyInstallerSpec = Join-Path $BuildRoot "spec"
$StagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("${ProjectName}_exe_release_" + [guid]::NewGuid().ToString("N"))
$PayloadRoot = Join-Path $StagingRoot $ProjectName
$CommandsData = (Join-Path $ProjectRoot "config\commands.yaml") + ";config"
$DevicesExampleData = (Join-Path $ProjectRoot "config\devices.example.yaml") + ";config"

try {
    Push-Location $ProjectRoot
    try {
        python -m PyInstaller `
            --noconfirm `
            --clean `
            --windowed `
            --onefile `
            --name $ExeName `
            --paths $ProjectRoot `
            --paths $ParentDir `
            --add-data $CommandsData `
            --add-data $DevicesExampleData `
            --distpath $PyInstallerDist `
            --workpath $PyInstallerWork `
            --specpath $PyInstallerSpec `
            app.py
    } finally {
        Pop-Location
    }

    $ExePath = Join-Path $PyInstallerDist "${ExeName}.exe"
    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Executable was not created: $ExePath"
    }

    & $ExePath --smoke-check
    if ($LASTEXITCODE -ne 0) {
        throw "Executable smoke check failed with exit code $LASTEXITCODE"
    }

    New-Item -ItemType Directory -Force -Path $PayloadRoot | Out-Null
    Copy-Item -LiteralPath $ExePath -Destination (Join-Path $PayloadRoot "${ExeName}.exe") -Force
    Copy-DirectoryContent -Source (Join-Path $ProjectRoot "config") -Destination (Join-Path $PayloadRoot "config")
    Copy-DirectoryContent -Source (Join-Path $ProjectRoot "docs") -Destination (Join-Path $PayloadRoot "docs")
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination (Join-Path $PayloadRoot "README.md") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "CHANGELOG.md") -Destination (Join-Path $PayloadRoot "CHANGELOG.md") -Force

    $runText = @"
Backbone State Tracker v$Version

1. Run BackboneStateTracker.exe.
2. Edit config\devices.example.yaml or save device entries from the GUI.
3. Runtime outputs are created under outputs\snapshots next to the executable.

Security note:
- No password is saved by the program.
- Corporate mail systems may block ZIP files that contain EXE files.
- If email upload is blocked, use the approved internal file transfer process.
"@
    Set-Content -LiteralPath (Join-Path $PayloadRoot "RUN_FIRST.txt") -Value $runText -Encoding UTF8

    Compress-Archive -LiteralPath $PayloadRoot -DestinationPath $ZipPath -CompressionLevel Optimal
} finally {
    if (Test-Path -LiteralPath $BuildRoot) {
        Remove-Item -LiteralPath $BuildRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
}

Write-Host "Windows EXE ZIP created: $ZipPath"
