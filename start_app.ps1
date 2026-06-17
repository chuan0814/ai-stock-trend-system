$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"
$appFile = Join-Path $PSScriptRoot "app.py"
$packageDir = Join-Path $PSScriptRoot ".python_packages"
$depsMarker = Join-Path $packageDir ".deps_ready"
$bundledPython = "C:\Users\chuan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

function Get-BootstrapPython {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notlike "*WindowsApps*") {
        return $pythonCommand.Source
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return "py"
    }

    if (Test-Path $bundledPython) {
        return $bundledPython
    }

    throw "Python not found. Please install Python first, or reopen Codex and try again."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    if ($PythonPath -eq "py") {
        & py @Arguments
        return
    }

    & $PythonPath @Arguments
}

function Test-RequiredModules {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath
    )

    $testCode = @"
import importlib.util
modules = ["streamlit", "requests", "pandas", "numpy", "plotly", "openai"]
missing = [name for name in modules if importlib.util.find_spec(name) is None]
print(",".join(missing))
"@

    if ($PythonPath -eq "py") {
        $output = & py -c $testCode
    }
    else {
        $output = & $PythonPath -c $testCode
    }

    return ($output | Out-String).Trim()
}

function Ensure-PackageFolder {
    if (-not (Test-Path $packageDir)) {
        New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
    }
}

function Ensure-Dependencies {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath
    )

    if (-not (Test-Path $requirementsFile)) {
        throw "requirements.txt was not found."
    }

    Ensure-PackageFolder

    $needsInstall = -not (Test-Path $depsMarker)
    if (-not $needsInstall) {
        $requirementsTime = (Get-Item $requirementsFile).LastWriteTimeUtc
        $markerTime = (Get-Item $depsMarker).LastWriteTimeUtc
        if ($requirementsTime -gt $markerTime) {
            $needsInstall = $true
        }
    }

    $missingModules = Test-RequiredModules -PythonPath $PythonPath
    if ($missingModules) {
        $needsInstall = $true
    }

    if (-not $needsInstall) {
        return
    }

    Write-Host ""
    Write-Host "Installing required packages. This can take a few minutes on the first run..."

    Invoke-Python -PythonPath $PythonPath -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed while upgrading pip."
    }

    Invoke-Python -PythonPath $PythonPath -Arguments @("-m", "pip", "install", "--upgrade", "--target", $packageDir, "-r", $requirementsFile)
    if ($LASTEXITCODE -ne 0) {
        throw "Failed while installing packages from requirements.txt."
    }

    New-Item -ItemType File -Path $depsMarker -Force | Out-Null
}

try {
    if (-not (Test-Path $appFile)) {
        throw "app.py was not found."
    }

    $pythonPath = Get-BootstrapPython

    Write-Host "Preparing the AI stock analysis app..."

    Ensure-Dependencies -PythonPath $pythonPath

    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$packageDir;$env:PYTHONPATH"
    }
    else {
        $env:PYTHONPATH = $packageDir
    }
    $env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

    Write-Host ""
    Write-Host "Starting Streamlit..."
    Write-Host "If your browser does not open by itself, copy the Local URL from this window into your browser."
    Write-Host ""

    Invoke-Python -PythonPath $pythonPath -Arguments @("-m", "streamlit", "run", $appFile)
    exit $LASTEXITCODE
}
catch {
    Write-Host ""
    Write-Host "Start failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to close this window"
    exit 1
}
