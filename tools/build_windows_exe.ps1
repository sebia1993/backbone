param(
    [switch]$SkipTests,
    [string]$ReleaseTag
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectName = "backbone_state_tracker"
$GuiExeName = "BackboneStateTracker"
$WebExeName = "BackboneWebApp"
$ParentDir = Split-Path $ProjectRoot -Parent
$DistDir = Join-Path $ProjectRoot "dist"
$VersionFile = Join-Path $ProjectRoot "core\version.py"

$SourceCommit = (git -C $ProjectRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $SourceCommit -notmatch '^[0-9a-f]{40}$') {
    throw "Unable to resolve the source commit for release provenance."
}

$versionText = Get-Content -LiteralPath $VersionFile -Raw
if ($versionText -notmatch 'APP_VERSION\s*=\s*"([^"]+)"') {
    throw "Unable to read APP_VERSION from $VersionFile"
}
$Version = $Matches[1]
if ($versionText -notmatch 'APP_RELEASE_DATE\s*=\s*"(\d{4})-(\d{2})-(\d{2})"') {
    throw "Unable to read APP_RELEASE_DATE from $VersionFile"
}
$DateStamp = "$($Matches[1])$($Matches[2])$($Matches[3])"
if ([string]::IsNullOrWhiteSpace($ReleaseTag)) {
    $ReleaseTag = "v$Version"
}
$ZipName = "${ProjectName}_${ReleaseTag}_windows.zip"
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
            if ($LASTEXITCODE -ne 0) { throw "Unit tests failed with exit code $LASTEXITCODE" }
            python app.py --smoke-check
            if ($LASTEXITCODE -ne 0) { throw "GUI smoke check failed with exit code $LASTEXITCODE" }
            python webapp_launcher.py --smoke
            if ($LASTEXITCODE -ne 0) { throw "Webapp smoke check failed with exit code $LASTEXITCODE" }
        } finally {
            Pop-Location
        }
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }
}

function Copy-ShareableConfig {
    param([string]$Destination)

    $shareableNames = @(
        "analysis_rules.yaml",
        "commands.yaml",
        "devices.example.yaml",
        "known_hosts.example",
        "mock_profiles.yaml"
    )
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    foreach ($name in $shareableNames) {
        $source = Join-Path (Join-Path $ProjectRoot "config") $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            throw "Required shareable config is missing: $source"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $Destination $name) -Force
    }
}

function Update-LatestReleaseArtifacts {
    param(
        [string]$ProjectName,
        [string]$ReleaseTag,
        [string]$DistDir
    )

    $LatestDir = Join-Path $DistDir "latest"
    if (Test-Path -LiteralPath $LatestDir) {
        Remove-Item -LiteralPath $LatestDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $LatestDir | Out-Null

    $prefix = "${ProjectName}_${ReleaseTag}_"
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
        "태그 = $ReleaseTag",
        "생성 시각 = $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")",
        "",
        "GitHub Release에는 Windows ZIP, SHA-256 sidecar, manifest, SBOM을 독립 asset으로 업로드합니다.",
        "ZIP의 GitHub artifact attestation도 함께 검증합니다.",
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
    param([string]$Path)

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

function Invoke-PyInstallerBuild {
    param(
        [string]$EntryPoint,
        [string]$Name,
        [switch]$Windowed,
        [string]$DistPath,
        [string]$WorkPath,
        [string]$SpecPath
    )

    $CommandsData = (Join-Path $ProjectRoot "config\commands.yaml") + ";config"
    $DevicesExampleData = (Join-Path $ProjectRoot "config\devices.example.yaml") + ";config"
    $MockProfilesData = (Join-Path $ProjectRoot "config\mock_profiles.yaml") + ";config"
    $AnalysisRulesData = (Join-Path $ProjectRoot "config\analysis_rules.yaml") + ";config"
    $DocsData = (Join-Path $ProjectRoot "docs") + ";docs"
    $modeArgument = if ($Windowed) { "--windowed" } else { "--console" }

    Push-Location $ProjectRoot
    try {
        python -m PyInstaller `
            --noconfirm `
            --clean `
            $modeArgument `
            --onefile `
            --name $Name `
            --paths $ProjectRoot `
            --paths $ParentDir `
            --add-data $CommandsData `
            --add-data $DevicesExampleData `
            --add-data $MockProfilesData `
            --add-data $AnalysisRulesData `
            --add-data $DocsData `
            --distpath $DistPath `
            --workpath $WorkPath `
            --specpath $SpecPath `
            $EntryPoint
        if ($LASTEXITCODE -ne 0) {
            throw "$Name PyInstaller build failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }

    $exePath = Join-Path $DistPath "${Name}.exe"
    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Executable was not created: $exePath"
    }
    return $exePath
}

if (-not $SkipTests) {
    Invoke-SourceValidation
}

python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is not available." }

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

$BuildRoot = Join-Path $ProjectRoot ("build\pyinstaller_" + [guid]::NewGuid().ToString("N"))
$PyInstallerDist = Join-Path $BuildRoot "dist"
$PyInstallerWork = Join-Path $BuildRoot "work"
$PyInstallerSpec = Join-Path $BuildRoot "spec"
$StagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("${ProjectName}_windows_release_" + [guid]::NewGuid().ToString("N"))
$PayloadRoot = Join-Path $StagingRoot $ProjectName
$GuiRoot = Join-Path $PayloadRoot "gui"
$WebRoot = Join-Path $PayloadRoot "web"
$WebRuntimeRoot = Join-Path $WebRoot "runtime"

try {
    $GuiExePath = Invoke-PyInstallerBuild `
        -EntryPoint "app.py" `
        -Name $GuiExeName `
        -Windowed `
        -DistPath $PyInstallerDist `
        -WorkPath $PyInstallerWork `
        -SpecPath $PyInstallerSpec

    $WebExePath = Invoke-PyInstallerBuild `
        -EntryPoint "webapp_launcher.py" `
        -Name $WebExeName `
        -DistPath $PyInstallerDist `
        -WorkPath $PyInstallerWork `
        -SpecPath $PyInstallerSpec

    Invoke-ExecutableCheck -ExePath $GuiExePath -Arguments @("--smoke-check") -Description "GUI executable smoke check"
    Invoke-ExecutableCheck -ExePath $WebExePath -Arguments @("--smoke") -Description "Webapp executable smoke check"

    New-Item -ItemType Directory -Force -Path $GuiRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $WebRuntimeRoot | Out-Null
    Copy-Item -LiteralPath $GuiExePath -Destination (Join-Path $GuiRoot "${GuiExeName}.exe") -Force
    Copy-Item -LiteralPath $WebExePath -Destination (Join-Path $WebRuntimeRoot "${WebExeName}.exe") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination (Join-Path $PayloadRoot "LICENSE") -Force
    Copy-ShareableConfig -Destination (Join-Path $GuiRoot "config")
    Copy-ShareableConfig -Destination (Join-Path $WebRoot "config")

    $startWebappText = @"
@echo off
setlocal
set "APP_DIR=%~dp0"
"%APP_DIR%runtime\${WebExeName}.exe" %*
"@
    Set-Content -LiteralPath (Join-Path $WebRoot "start_webapp.cmd") -Value $startWebappText -Encoding ASCII

    $readmeStartText = @"
백본 상태 추적기 Windows 통합 ZIP
태그: $ReleaseTag
앱 버전: v$Version

1. 다운로드할 파일
- GitHub Release에서 ${ProjectName}_${ReleaseTag}_windows.zip, SHA-256 sidecar, release manifest, CycloneDX SBOM을 함께 받습니다.
- GitHub가 자동으로 표시하는 Source code (zip)와 Source code (tar.gz)는 소스 아카이브이며 일반 사용자가 실행할 파일이 아닙니다.

2. GUI 실행 방법
- ZIP을 원하는 폴더에 압축 해제합니다.
- 보안 담당자 또는 장비 콘솔에서 별도 채널로 확인한 fingerprint와 일치하는 키만 gui\config\known_hosts에 등록합니다.
- gui\config\known_hosts가 없거나 비어 있거나 주석뿐이거나 형식이 잘못되면 실제 장비 접속 전에 수집이 차단됩니다.
- gui\${GuiExeName}.exe를 더블클릭합니다.
- 첫 화면 장비 설정에서 장비 정보와 계정을 입력합니다.

3. 웹앱 실행 방법
- web\start_webapp.cmd를 더블클릭합니다.
- 기본 주소는 http://127.0.0.1:8765/ 입니다.
- 브라우저가 자동으로 열리지 않으면 위 주소를 직접 입력합니다.

4. 웹앱 포트/설정 변경
- 포트를 바꾸려면 명령 프롬프트에서 web\start_webapp.cmd --port 8777 처럼 실행합니다.
- 외부 공개용 서버가 아니라 로컬 PC 확인용 웹앱입니다. 기본값인 127.0.0.1 사용을 권장합니다.

5. 포함/제외 기준
- 사용자 실행물은 GUI와 웹앱이며, 시작 안내와 MIT LICENSE를 함께 포함합니다.
- 루트 LICENSE에 이 배포본의 MIT 허가 고지를 포함합니다.
- CLI 실행 파일과 CLI 실행 안내는 최종 사용자용 ZIP에 포함하지 않습니다.
- 실제 known_hosts와 devices.yaml은 배포 ZIP에 포함하지 않습니다. known_hosts.example은 형식 안내입니다.
"@
    Set-Content -LiteralPath (Join-Path $PayloadRoot "README_START_HERE_KO.txt") -Value $readmeStartText -Encoding UTF8

    $guiReadmeText = @"
GUI 실행 안내

- 실행 파일: gui\${GuiExeName}.exe
- Python 설치 없이 더블클릭으로 실행합니다.
- 설정 예시는 gui\config\devices.example.yaml을 참고합니다.
- 실제 장비 정보가 들어간 devices.yaml은 배포 ZIP에 포함하지 않습니다.
- 별도 채널로 확인한 호스트 키를 gui\config\known_hosts에 등록해야 실제 수집을 시작할 수 있습니다.
- gui\config\known_hosts.example은 설명용이며 신뢰 키를 포함하지 않습니다.
"@
    Set-Content -LiteralPath (Join-Path $GuiRoot "README_GUI_KO.txt") -Value $guiReadmeText -Encoding UTF8

    $webReadmeText = @"
웹앱 실행 안내

- 실행 파일: web\start_webapp.cmd
- 기본 주소: http://127.0.0.1:8765/
- 포트 변경: web\start_webapp.cmd --port 8777
- smoke 확인: web\start_webapp.cmd --smoke
- Python 또는 별도 런타임 설치 없이 실행됩니다.
"@
    Set-Content -LiteralPath (Join-Path $WebRoot "README_WEB_KO.txt") -Value $webReadmeText -Encoding UTF8

    $packageInfoText = @"
백본 상태 추적기 v$Version
패키지 태그: $ReleaseTag
패키지 형식: Windows 통합 ZIP
생성 시각: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")

포함 항목:
- README_START_HERE_KO.txt
- LICENSE
- gui\${GuiExeName}.exe
- gui\config 공유 설정 예시
- web\start_webapp.cmd
- web\runtime\${WebExeName}.exe
- web\config 공유 설정 예시

제외 항목:
- CLI 실행 파일과 CLI 전용 안내
- 실행 중 생성되는 outputs 등 런타임 산출물
- 내부 장비 정보가 들어갈 수 있는 로컬 config\devices.yaml
- 로컬에서 승인한 SSH 공개 호스트 키 config\known_hosts
- 소스 저장소 메타데이터와 빌드 작업 폴더

검증:
- GUI smoke check
- 웹앱 smoke check
- 통합 ZIP 구조 verifier
- ZIP/SHA-256/manifest/SBOM 독립 검증과 GitHub artifact attestation
"@
    Set-Content -LiteralPath (Join-Path $PayloadRoot "PACKAGE_INFO.txt") -Value $packageInfoText -Encoding UTF8

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
python $ManifestTool --project-name $ProjectName --version $Version --date-stamp $DateStamp --dist-dir $DistDir --package $ZipPath --release-tag $ReleaseTag --source-commit $SourceCommit
if ($LASTEXITCODE -ne 0) {
    throw "Release manifest generation failed with exit code $LASTEXITCODE"
}

$VerifierTool = Join-Path $ProjectRoot "tools\verify_release_package.py"
python $VerifierTool $ZipPath --type windows --require-manifest
if ($LASTEXITCODE -ne 0) {
    throw "Release package verification failed with exit code $LASTEXITCODE"
}

$PowerShellVerifierSource = Join-Path $ProjectRoot "tools\verify_release_package.ps1"
$PowerShellExecutable = (Get-Process -Id $PID).Path
& $PowerShellExecutable -NoLogo -NoProfile -ExecutionPolicy Bypass -File $PowerShellVerifierSource -Package $ZipPath -Type windows -RequireManifest
if ($LASTEXITCODE -ne 0) {
    throw "PowerShell release package verification failed with exit code $LASTEXITCODE"
}
$PowerShellVerifierTarget = Join-Path $DistDir "${ProjectName}_${ReleaseTag}_verify_release_package.ps1"
Copy-Item -LiteralPath $PowerShellVerifierSource -Destination $PowerShellVerifierTarget -Force
Update-LatestReleaseArtifacts -ProjectName $ProjectName -ReleaseTag $ReleaseTag -DistDir $DistDir

Write-Host "Windows integrated ZIP created: $ZipPath"
