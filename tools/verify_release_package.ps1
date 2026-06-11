param(
    [Parameter(Mandatory = $true)]
    [string]$Package,

    [ValidateSet("source", "windows_exe", "unknown")]
    [string]$Type = "unknown",

    [switch]$RequireManifest
)

$ErrorActionPreference = "Stop"

function Get-NormalizedZipEntries {
    param([string]$PackagePath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($PackagePath)
    try {
        return @($archive.Entries | ForEach-Object { $_.FullName.Replace("\", "/") })
    } finally {
        $archive.Dispose()
    }
}

function Get-PackageType {
    param([string]$PackageName)

    $lowerName = $PackageName.ToLowerInvariant()
    if ($lowerName.EndsWith("_source.zip")) {
        return "source"
    }
    if ($lowerName.EndsWith("_windows_exe.zip")) {
        return "windows_exe"
    }
    return "unknown"
}

function Get-ExpectedManifestName {
    param([string]$PackageName)

    if ($PackageName -match "^(?<prefix>.+_v\d+\.\d+\.\d+_\d{8})_(source|windows_exe)\.zip$") {
        return "$($Matches["prefix"])_release_manifest.txt"
    }
    return $null
}

$resolvedPackage = (Resolve-Path -LiteralPath $Package).Path
$packageItem = Get-Item -LiteralPath $resolvedPackage
$packageName = $packageItem.Name
$packageType = if ($Type -eq "unknown") { Get-PackageType -PackageName $packageName } else { $Type }
$sidecarPath = "$resolvedPackage.sha256.txt"
$errors = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

if (-not (Test-Path -LiteralPath $sidecarPath)) {
    $errors.Add("Missing checksum sidecar: $(Split-Path $sidecarPath -Leaf)")
} else {
    $sidecarText = Get-Content -LiteralPath $sidecarPath -Raw -Encoding UTF8
    $multiline = [System.Text.RegularExpressions.RegexOptions]::Multiline
    $shaMatch = [regex]::Match($sidecarText, "^SHA256 \((?<name>.+)\) = (?<sha256>[0-9a-f]{64})\r?$", $multiline)
    $sizeMatch = [regex]::Match($sidecarText, "^Size = (?<size>\d+) bytes\r?$", $multiline)
    if (-not $shaMatch.Success) {
        $errors.Add("Checksum sidecar does not contain a SHA256 line: $(Split-Path $sidecarPath -Leaf)")
    }
    if (-not $sizeMatch.Success) {
        $errors.Add("Checksum sidecar does not contain a Size line: $(Split-Path $sidecarPath -Leaf)")
    }
    if ($shaMatch.Success) {
        $expectedSha = $shaMatch.Groups["sha256"].Value
        $actualSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedPackage).Hash.ToLowerInvariant()
        if ($actualSha -ne $expectedSha) {
            $errors.Add("SHA256 mismatch for ${packageName}: expected $expectedSha, actual $actualSha")
        }
    }
    if ($sizeMatch.Success) {
        $expectedSize = [int64]$sizeMatch.Groups["size"].Value
        if ($packageItem.Length -ne $expectedSize) {
            $errors.Add("Size mismatch for ${packageName}: expected $expectedSize, actual $($packageItem.Length)")
        }
    }
}

$commonRequired = @(
    "backbone_state_tracker/PACKAGE_INFO.txt",
    "backbone_state_tracker/README.md",
    "backbone_state_tracker/CHANGELOG.md",
    "backbone_state_tracker/config/commands.yaml",
    "backbone_state_tracker/config/devices.example.yaml",
    "backbone_state_tracker/docs/USER_GUIDE.md",
    "backbone_state_tracker/docs/USER_GUIDE.html",
    "backbone_state_tracker/docs/COMMAND_GUIDE.md",
    "backbone_state_tracker/docs/COMMAND_GUIDE.html",
    "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.md",
    "backbone_state_tracker/docs/DEVELOPER_GUIDE_BEGINNER.html",
    "backbone_state_tracker/docs/VERSION_HISTORY.md",
    "backbone_state_tracker/docs/VERSION_HISTORY.html"
)
$sourceRequired = $commonRequired + @(
    "backbone_state_tracker/app.py",
    "backbone_state_tracker/core/version.py",
    "backbone_state_tracker/tools/build_release.ps1",
    "backbone_state_tracker/tools/build_windows_exe.ps1",
    "backbone_state_tracker/tools/write_release_manifest.py",
    "backbone_state_tracker/tools/verify_release_package.py",
    "backbone_state_tracker/tools/verify_release_package.ps1",
    "backbone_state_tracker/tests/test_release_manifest.py",
    "backbone_state_tracker/tests/test_release_package_verifier.py"
)
$exeRequired = $commonRequired + @(
    "backbone_state_tracker/BackboneStateTracker.exe",
    "backbone_state_tracker/RUN_FIRST.txt"
)
$required = switch ($packageType) {
    "source" { $sourceRequired }
    "windows_exe" { $exeRequired }
    default { $commonRequired }
}

$entries = Get-NormalizedZipEntries -PackagePath $resolvedPackage
$entrySet = @{}
foreach ($entry in $entries) {
    $entrySet[$entry] = $true
}
foreach ($requiredEntry in $required) {
    if (-not $entrySet.ContainsKey($requiredEntry)) {
        $errors.Add("Missing required ZIP entry: $requiredEntry")
    }
}

$forbiddenPatterns = @(
    "/\.git/",
    "/outputs/",
    "/dist/",
    "/build/",
    "/raw/",
    "/config/devices\.yaml$",
    "__pycache__",
    "\.pyc$",
    "\.spec$"
)
foreach ($entry in $entries) {
    foreach ($pattern in $forbiddenPatterns) {
        if ($entry -match $pattern) {
            $errors.Add("Forbidden ZIP entry found: $entry")
            break
        }
    }
}

$manifestName = Get-ExpectedManifestName -PackageName $packageName
if ([string]::IsNullOrWhiteSpace($manifestName)) {
    $message = "Release manifest was not found next to the package."
    if ($RequireManifest) {
        $errors.Add($message)
    } else {
        $warnings.Add($message)
    }
} else {
    $manifestPath = Join-Path $packageItem.DirectoryName $manifestName
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        $message = "Release manifest was not found next to the package: $manifestName"
        if ($RequireManifest) {
            $errors.Add($message)
        } else {
            $warnings.Add($message)
        }
    } else {
        $manifestText = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
        if ($manifestText -notmatch [regex]::Escape($packageName)) {
            $errors.Add("Release manifest does not list package: $packageName")
        }
        if ($expectedSha -and $manifestText -notmatch [regex]::Escape($expectedSha)) {
            $errors.Add("Release manifest does not list package SHA256: $expectedSha")
        }
    }
}

Write-Host "Package: $resolvedPackage"
Write-Host "Type: $packageType"
if ($warnings.Count -gt 0) {
    Write-Host "Warnings:"
    foreach ($warning in $warnings) {
        Write-Host "- $warning"
    }
}
if ($errors.Count -gt 0) {
    Write-Host "Errors:"
    foreach ($errorMessage in $errors) {
        Write-Host "- $errorMessage"
    }
    exit 1
}

Write-Host "Verification OK"
