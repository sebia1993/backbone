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

function Write-CheckLog {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if (-not [string]::IsNullOrWhiteSpace($text)) {
        Write-Host $text.TrimEnd()
    }
}

function Invoke-ExecutableCheck {
    param(
        [string]$ExePath,
        [string[]]$Arguments,
        [string]$Description
    )

    $LogRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("${ProjectName}_exe_check_" + [guid]::NewGuid().ToString("N"))
    $StdoutPath = Join-Path $LogRoot "stdout.log"
    $StderrPath = Join-Path $LogRoot "stderr.log"

    try {
        New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
        $process = Start-Process `
            -FilePath $ExePath `
            -ArgumentList $Arguments `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $StdoutPath `
            -RedirectStandardError $StderrPath

        Write-CheckLog -Path $StdoutPath
        Write-CheckLog -Path $StderrPath

        if ($process.ExitCode -ne 0) {
            throw "$Description failed with exit code $($process.ExitCode)"
        }
    } finally {
        if (Test-Path -LiteralPath $LogRoot) {
            Remove-Item -LiteralPath $LogRoot -Recurse -Force -ErrorAction SilentlyContinue
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
$MockProfilesData = (Join-Path $ProjectRoot "config\mock_profiles.yaml") + ";config"
$AnalysisRulesData = (Join-Path $ProjectRoot "config\analysis_rules.yaml") + ";config"
$DocsData = (Join-Path $ProjectRoot "docs") + ";docs"

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
            --add-data $MockProfilesData `
            --add-data $AnalysisRulesData `
            --add-data $DocsData `
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

    Invoke-ExecutableCheck -ExePath $ExePath -Arguments @("--smoke-check") -Description "Executable smoke check"
    Invoke-ExecutableCheck -ExePath $ExePath -Arguments @("--diagnose", "--self-check") -Description "Executable diagnostic self-check"
    Invoke-ExecutableCheck -ExePath $ExePath -Arguments @("--mock-server", "--protocol", "telnet", "--profile", "normal", "--self-check") -Description "실행 파일 모의 Telnet 자체 점검"
    Invoke-ExecutableCheck -ExePath $ExePath -Arguments @("--mock-server", "--protocol", "ssh", "--profile", "normal", "--self-check") -Description "실행 파일 모의 SSH 자체 점검"

    New-Item -ItemType Directory -Force -Path $PayloadRoot | Out-Null
    Copy-Item -LiteralPath $ExePath -Destination (Join-Path $PayloadRoot "${ExeName}.exe") -Force
    Copy-DirectoryContent -Source (Join-Path $ProjectRoot "config") -Destination (Join-Path $PayloadRoot "config")
    $LocalDevicesConfig = Join-Path $PayloadRoot "config\devices.yaml"
    if (Test-Path -LiteralPath $LocalDevicesConfig) {
        Remove-Item -LiteralPath $LocalDevicesConfig -Force
    }
    Copy-DirectoryContent -Source (Join-Path $ProjectRoot "docs") -Destination (Join-Path $PayloadRoot "docs")
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination (Join-Path $PayloadRoot "README.md") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "RELEASE_NOTES.md") -Destination (Join-Path $PayloadRoot "RELEASE_NOTES.md") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "CHANGELOG.md") -Destination (Join-Path $PayloadRoot "CHANGELOG.md") -Force

    $packageInfoText = @"
백본 상태 추적기 v$Version
패키지 형식: Windows EXE ZIP
생성 시각: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")

포함 항목:
- BackboneStateTracker.exe
- 설정 예시 파일
- 운영자/개발자 가이드
- 진단 모드 가이드와 오류 코드 카탈로그
- 릴리스 노트 정책
- 버전 변경내역과 CHANGELOG

제외 항목:
- 실행 중 생성되는 outputs 등 런타임 산출물
- 내부 장비 정보가 들어갈 수 있는 로컬 config\devices.yaml
- 소스 저장소 메타데이터
- 빌드 작업 폴더

검증 방법:
- 이 ZIP 파일의 SHA256 값을 dist의 동일 이름 .sha256.txt 파일과 비교하세요.
- 버전 단위 release_manifest.txt 파일도 dist에 함께 생성됩니다.
"@
    Set-Content -LiteralPath (Join-Path $PayloadRoot "PACKAGE_INFO.txt") -Value $packageInfoText -Encoding UTF8

    $runText = @"
백본 상태 추적기 v$Version

1. BackboneStateTracker.exe를 실행합니다.
2. config\devices.example.yaml을 참고해 장비 정보를 입력하거나 GUI에서 장비 목록을 저장합니다.
3. 실행 결과는 EXE가 있는 폴더 아래 outputs\snapshots에 생성됩니다.
4. 실제 장비 없이 패키지를 점검하려면 아래 명령을 실행합니다.
   BackboneStateTracker.exe --diagnose --self-check
   BackboneStateTracker.exe --mock-server --protocol ssh --profile normal --self-check
   BackboneStateTracker.exe --mock-server --protocol telnet --profile normal --self-check

보안 안내:
- 이 프로그램은 비밀번호를 저장하지 않습니다.
- 일부 회사 메일 시스템은 EXE가 포함된 ZIP 업로드를 차단할 수 있습니다.
- 메일 업로드가 차단되면 승인된 사내 파일 반입 절차를 사용하세요.
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

$ManifestTool = Join-Path $ProjectRoot "tools\write_release_manifest.py"
python $ManifestTool --project-name $ProjectName --version $Version --date-stamp $DateStamp --dist-dir $DistDir --package $ZipPath
if ($LASTEXITCODE -ne 0) {
    throw "Release manifest generation failed with exit code $LASTEXITCODE"
}

$VerifierTool = Join-Path $ProjectRoot "tools\verify_release_package.py"
python $VerifierTool $ZipPath --type windows_exe --require-manifest
if ($LASTEXITCODE -ne 0) {
    throw "Release package verification failed with exit code $LASTEXITCODE"
}

$PowerShellVerifierSource = Join-Path $ProjectRoot "tools\verify_release_package.ps1"
$PowerShellVerifierTarget = Join-Path $DistDir "${ProjectName}_v${Version}_${DateStamp}_verify_release_package.ps1"
Copy-Item -LiteralPath $PowerShellVerifierSource -Destination $PowerShellVerifierTarget -Force
Update-LatestReleaseArtifacts -ProjectName $ProjectName -Version $Version -DateStamp $DateStamp -DistDir $DistDir

Write-Host "Windows EXE ZIP created: $ZipPath"
