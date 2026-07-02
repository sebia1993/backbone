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
            python app.py --smoke-check
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

function Update-LatestReleaseArtifacts {
    param(
        [string]$ProjectName,
        [string]$Version,
        [string]$DateStamp,
        [string]$DistDir
    )

    $LatestDir = Join-Path $DistDir "latest"
    if (Test-Path -LiteralPath $LatestDir) {
        Remove-Item -LiteralPath $LatestDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $LatestDir | Out-Null

    $prefix = "${ProjectName}_v${Version}_${DateStamp}_"
    $artifacts = @(
        Get-ChildItem -LiteralPath $DistDir -File |
            Where-Object { $_.Name -like "$prefix*" } |
            Sort-Object Name
    )

    foreach ($artifact in $artifacts) {
        Copy-Item -LiteralPath $artifact.FullName -Destination (Join-Path $LatestDir $artifact.Name) -Force
    }

    $currentReleaseLines = @(
        "백본 상태 추적기 최신 릴리스",
        "버전 = v$Version",
        "날짜 스탬프 = $DateStamp",
        "생성 시각 = $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")",
        "",
        "과거 ZIP이 dist에 함께 남아 있을 때는 사내 반입용 최신 파일을 dist\latest에서 확인하세요.",
        "",
        "산출물:"
    )
    foreach ($artifact in $artifacts) {
        $currentReleaseLines += " - $($artifact.Name) ($($artifact.Length) bytes)"
    }

    Set-Content -LiteralPath (Join-Path $DistDir "CURRENT_RELEASE.txt") -Value $currentReleaseLines -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $LatestDir "CURRENT_RELEASE.txt") -Value $currentReleaseLines -Encoding UTF8
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
백본 상태 추적기 v$Version
패키지 형식: Source ZIP
생성 시각: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")

포함 항목:
- 소스 코드
- 설정 예시 파일
- 운영자/개발자 가이드
- 릴리스 노트 정책
- 단위 테스트
- 릴리스 패키징 스크립트

제외 항목:
- .git
- outputs
- dist
- build
- 내부 장비 정보가 들어갈 수 있는 로컬 config\devices.yaml
- Python 캐시와 가상환경

검증 방법:
- 이 ZIP 파일의 SHA256 값을 dist의 동일 이름 .sha256.txt 파일과 비교하세요.
- 버전 단위 release_manifest.txt 파일도 dist에 함께 생성됩니다.
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
Update-LatestReleaseArtifacts -ProjectName $ProjectName -Version $Version -DateStamp $DateStamp -DistDir $DistDir

Write-Host "Release ZIP created: $ZipPath"
