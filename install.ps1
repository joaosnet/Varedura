# Varedura - Standalone Installer v1.0.0
# System Monitor & Docker Cleanup Tool
# https://github.com/joaosnet/Varedura
#
# Usage / Uso:
#   irm https://raw.githubusercontent.com/joaosnet/Varedura/main/install.ps1 | iex
#   or: .\install.ps1
#
#   Flags:
#     -Uninstall     Remove varedura from the system
#     -Check         Check dependencies only
#     -Lang en|pt    Force language
#

param (
    [Parameter(HelpMessage = "Uninstall varedura")]
    [switch]$Uninstall,

    [Parameter(HelpMessage = "Check dependencies only")]
    [switch]$Check,

    [Parameter(HelpMessage = "Force language (pt or en)")]
    [ValidateSet("pt", "en")]
    [string]$Lang,

    [Parameter(HelpMessage = "Print help")]
    [switch]$Help
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Config
$AppName    = "varedura"
$AppVersion = "1.0.0"
$RepoUrl    = "https://github.com/joaosnet/Varedura.git"

# Language detection
function Detect-Lang {
    try {
        $culture = (Get-Culture).Name
        if ($culture -like "pt*") { return "pt" }
    } catch {}
    return "en"
}

if (-not $Lang) { $Lang = Detect-Lang }

function Msg {
    param([string]$Key, [string]$A1 = "", [string]$A2 = "")

    if ($Lang -eq "pt") {
        switch ($Key) {
            "detecting_os"     { "[..] Detectando sistema operacional..." }
            "os_detected"      { "     Sistema : $A1 $A2" }
            "checking_deps"    { "`n[..] Verificando dependencias...`n" }
            "found"            { "     [+] $A1" }
            "missing"          { "     [-] $A1 -- nao encontrado" }
            "missing_optional" { "     [!] $A1 -- nao encontrado (opcional)" }
            "will_install"     { "     [>] $A1 sera instalado automaticamente" }
            "installing_dep"   { "`n[>>] Instalando $A1..." }
            "dep_ok"           { "     [+] $A1 instalado com sucesso" }
            "installing_app"   { "`n[>>] Instalando Varedura..." }
            "install_progress" { "     [..] Isso pode levar alguns minutos..." }
            "already_installed"{ "`n[!] Varedura ja esta instalado." }
            "choose_action"    { "     O que deseja fazer?`n`n     [R] Reinstalar   [U] Desinstalar   [C] Cancelar`n" }
            "confirm_install"  { "`nDeseja prosseguir com a instalacao? [S/n]: " }
            "uninstalling"     { "`n[>>] Desinstalando Varedura..." }
            "uninstall_ok"     { "`n[+] Varedura desinstalado com sucesso." }
            "not_installed"    { "`n[!] Varedura nao esta instalado." }
            "abort"            { "`n[-] Operacao cancelada." }
            "error"            { "`n[-] Erro: $A1" }
            "summary_hdr"      { "`n[i] Resumo da instalacao:" }
            "sum_os"           { "     Sistema       : $A1" }
            "sum_install"      { "     A instalar    : $A1" }
            "sum_ok"           { "     Ja presente   : $A1" }
            "restart_hint"     { "`n[!] Reinicie o terminal para que o comando 'varedura' funcione." }
            "path_hint"        { "[!] Certifique-se de que $A1 esta no seu PATH." }
            "unsupported_os"   { "[-] Sistema operacional nao suportado: $A1" }
            "uv_manages_py"    { "(uv gerencia a versao automaticamente)" }
            "check_ready"      { "`n[+] Todas as dependencias obrigatorias estao presentes." }
            "check_missing"    { "`n[-] Dependencias obrigatorias faltando: $A1" }
            default            { $Key }
        }
    } else {
        switch ($Key) {
            "detecting_os"     { "[..] Detecting operating system..." }
            "os_detected"      { "     System  : $A1 $A2" }
            "checking_deps"    { "`n[..] Checking dependencies...`n" }
            "found"            { "     [+] $A1" }
            "missing"          { "     [-] $A1 -- not found" }
            "missing_optional" { "     [!] $A1 -- not found (optional)" }
            "will_install"     { "     [>] $A1 will be installed automatically" }
            "installing_dep"   { "`n[>>] Installing $A1..." }
            "dep_ok"           { "     [+] $A1 installed successfully" }
            "installing_app"   { "`n[>>] Installing Varedura..." }
            "install_progress" { "     [..] This may take a few minutes..." }
            "already_installed"{ "`n[!] Varedura is already installed." }
            "choose_action"    { "     What would you like to do?`n`n     [R] Reinstall   [U] Uninstall   [C] Cancel`n" }
            "confirm_install"  { "`nProceed with installation? [Y/n]: " }
            "uninstalling"     { "`n[>>] Uninstalling Varedura..." }
            "uninstall_ok"     { "`n[+] Varedura uninstalled successfully." }
            "not_installed"    { "`n[!] Varedura is not installed." }
            "abort"            { "`n[-] Operation cancelled." }
            "error"            { "`n[-] Error: $A1" }
            "summary_hdr"      { "`n[i] Installation summary:" }
            "sum_os"           { "     System        : $A1" }
            "sum_install"      { "     To install    : $A1" }
            "sum_ok"           { "     Already there : $A1" }
            "restart_hint"     { "`n[!] Restart your terminal for the 'varedura' command to work." }
            "path_hint"        { "[!] Make sure $A1 is in your PATH." }
            "unsupported_os"   { "[-] Unsupported operating system: $A1" }
            "uv_manages_py"    { "(uv manages the version automatically)" }
            "check_ready"      { "`n[+] All required dependencies are present." }
            "check_missing"    { "`n[-] Missing required dependencies: $A1" }
            default            { $Key }
        }
    }
}

function Say {
    param([string]$Key, [string]$A1 = "", [string]$A2 = "")
    $text = Msg $Key $A1 $A2
    # Colorize based on prefix
    if ($text -match "^\s*\[\+\]") {
        Write-Host $text -ForegroundColor Green
    } elseif ($text -match "^\s*\[-\]") {
        Write-Host $text -ForegroundColor Red
    } elseif ($text -match "^\s*\[!\]") {
        Write-Host $text -ForegroundColor Yellow
    } elseif ($text -match "^\s*\[>") {
        Write-Host $text -ForegroundColor Cyan
    } elseif ($text -match "^\s*\[\.\.]") {
        Write-Host $text -ForegroundColor DarkGray
    } elseif ($text -match "^\s*\[i\]") {
        Write-Host $text -ForegroundColor White
    } else {
        Write-Host $text
    }
}

# Banner
function Print-Banner {
    Write-Host ""
    Write-Host "    ##   ## #####  ####  ##### ####  ##  ## ####   ####  " -ForegroundColor Cyan
    Write-Host "    ##   ## ##  ## ## ## ##     ## ## ##  ## ## ##  ##  ## " -ForegroundColor Cyan
    Write-Host "    ##   ## ##### ####  ####  ##  ## ##  ## ####  ###### " -ForegroundColor Cyan
    Write-Host "     ## ##  ##  ## ## ## ##     ## ## ##  ## ## ## ##  ## " -ForegroundColor Cyan
    Write-Host "      ###   ##  ## ## ## ##### ####   ####  ## ## ##  ## " -ForegroundColor Cyan
    Write-Host ""
    if ($Lang -eq "pt") {
        Write-Host "        Varedura Installer v$AppVersion" -ForegroundColor White
        Write-Host "        Monitor de Sistema e Limpeza Docker" -ForegroundColor DarkGray
    } else {
        Write-Host "        Varedura Installer v$AppVersion" -ForegroundColor White
        Write-Host "        System Monitor and Docker Cleanup Tool" -ForegroundColor DarkGray
    }
    Write-Host ""
}

# ═══════════════════════════ Helpers ══════════════════════════════════════
function Test-CmdAvailable { param([string]$Name); $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }

function Get-CmdVersion {
    param([string]$Cmd)
    try {
        $output = & $Cmd --version 2>&1 | Select-Object -First 1
        return "$output".Trim()
    } catch { return "" }
}

function Confirm-Yes {
    param([string]$PromptKey)
    $prompt = Msg $PromptKey
    Write-Host $prompt -NoNewline -ForegroundColor Cyan
    $answer = Read-Host
    if ([string]::IsNullOrWhiteSpace($answer)) { $answer = "y" }
    return ($answer -notmatch "^[nN]")
}

function Ask-Action {
    Say "choose_action"
    Write-Host "   > " -NoNewline -ForegroundColor Cyan
    $answer = Read-Host
    switch -Regex ($answer) {
        "^[rR]" { return "reinstall" }
        "^[uU]" { return "uninstall" }
        default  { return "cancel" }
    }
}

# ═══════════════════════════ OS Detection ═════════════════════════════════
function Detect-OS {
    Say "detecting_os"

    $arch = if ([System.Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
    try {
        $runtimeArch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        $arch = $runtimeArch.ToLower()
    } catch {}

    $osName = "Windows"
    $osDetail = "Windows $([System.Environment]::OSVersion.Version)"

    Say "os_detected" "$osName $arch" "($osDetail)"

    return @{
        Type   = "windows"
        Name   = $osName
        Arch   = $arch
        Detail = $osDetail
    }
}

# ═══════════════════════════ Dependency Check ═════════════════════════════
function Check-Dependencies {
    Say "checking_deps"

    $script:ToInstall = @()
    $script:AlreadyOK = @()

    # ── Python ──
    $pyCmd = $null
    # Skip Windows Store alias (returns exit code 9009)
    if (Test-CmdAvailable "python3") { $pyCmd = "python3" }
    if (-not $pyCmd -and (Test-CmdAvailable "python")) {
        try {
            $testPy = & python --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$testPy" -match "Python") { $pyCmd = "python" }
        } catch {}
    }

    if ($pyCmd) {
        $pyManages = Msg "uv_manages_py"
        try {
            $verStr = & $pyCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1
            if ($LASTEXITCODE -eq 0 -and "$verStr" -match "^\d+\.\d+") {
                $parts = "$verStr".Split(".")
                if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 14) {
                    Say "found" ("Python".PadRight(20) + "($verStr)")
                } else {
                    Say "found" ("Python".PadRight(20) + "($verStr) -- $pyManages")
                }
            } else {
                Say "found" ("Python".PadRight(20) + "-- $pyManages")
            }
        } catch {
            Say "found" ("Python".PadRight(20) + "-- $pyManages")
        }
        $script:AlreadyOK += "Python"
    } else {
        Say "found" ("Python".PadRight(20) + "-- $( Msg 'uv_manages_py' )")
    }

    # ── uv ──
    if (Test-CmdAvailable "uv") {
        $uvVer = Get-CmdVersion "uv"
        Say "found" ("uv".PadRight(20) + "($uvVer)")
        $script:AlreadyOK += "uv"
    } else {
        Say "missing" "uv (package manager)"
        Say "will_install" "uv"
        $script:ToInstall += "uv"
    }

    # ── Docker (optional) ──
    if (Test-CmdAvailable "docker") {
        $dockerVer = Get-CmdVersion "docker"
        Say "found" ("Docker".PadRight(20) + "($dockerVer)")
        $script:AlreadyOK += "Docker"
    } else {
        Say "missing_optional" "Docker"
    }

    # ── Git (optional) ──
    if (Test-CmdAvailable "git") {
        $gitVer = Get-CmdVersion "git"
        Say "found" ("Git".PadRight(20) + "($gitVer)")
        $script:AlreadyOK += "Git"
    } else {
        Say "missing_optional" "Git"
    }
}

# ═══════════════════════════ PATH Management ══════════════════════════════
function Refresh-InstallerPath {
    $home = $env:USERPROFILE
    $candidates = @(
        "$home\.local\bin",
        "$home\.cargo\bin"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) {
            if ($env:PATH -notlike "*$p*") {
                $env:PATH = "$p;$env:PATH"
            }
        }
    }
}

function Add-ToUserPath {
    param([string]$Dir)
    if (-not (Test-Path $Dir)) { return }

    $regPath = "registry::HKEY_CURRENT_USER\Environment"
    $currentPath = (Get-Item -LiteralPath $regPath).GetValue("Path", "", "DoNotExpandEnvironmentNames")
    $dirs = $currentPath -split ";" | Where-Object { $_ -ne "" }

    if ($Dir -in $dirs) { return }

    $newPath = ($Dir, $currentPath | Where-Object { $_ }) -join ";"
    Set-ItemProperty -Path $regPath -Name "Path" -Value $newPath -Type ExpandString

    # Notify the system of the environment change
    if (-not ([System.Management.Automation.PSTypeName]'NativeMethods').Type) {
        Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @"
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(
    IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
    uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
"@
    }
    $HWND_BROADCAST = [IntPtr]0xffff
    $WM_SETTINGCHANGE = 0x1a
    $result = [UIntPtr]::Zero
    [Win32.NativeMethods]::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE,
        [UIntPtr]::Zero, "Environment", 2, 5000, [ref]$result) | Out-Null
}

# ═══════════════════════════ Installation ═════════════════════════════════
function Install-Uv {
    Say "installing_dep" "uv"

    try {
        & ([scriptblock]::Create((Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing).Content))
    } catch {
        Say "error" $_.Exception.Message
        return $false
    }

    Refresh-InstallerPath

    if (Test-CmdAvailable "uv") {
        $ver = Get-CmdVersion "uv"
        Say "dep_ok" "uv ($ver)"
        return $true
    }

    Say "restart_hint"
    return $true
}

function Install-Varedura {
    param($OsInfo)

    Say "installing_app"
    Say "install_progress"

    # Determine source: local repo or remote git
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $pyprojectPath = Join-Path $scriptDir "pyproject.toml"

    if (Test-Path $pyprojectPath) {
        $source = $scriptDir
    } else {
        $source = "git+$RepoUrl"
    }

    $uvCmd = (Get-Command "uv" -ErrorAction SilentlyContinue).Source
    if (-not $uvCmd) { $uvCmd = "uv" }

    try {
        $result = & $uvCmd tool install $source --force --python ">=3.14" 2>&1
        $exitCode = $LASTEXITCODE
        if ($result) { Write-Host ($result -join "`n") }

        if ($exitCode -ne 0) {
            Say "error" "uv tool install failed (exit code: $exitCode)"
            return $false
        }

        Refresh-InstallerPath

        # Add uv tool bin dir to user PATH permanently
        $toolBin = Join-Path $env:USERPROFILE ".local\bin"
        if (Test-Path $toolBin) {
            Add-ToUserPath $toolBin
        }

        return $true
    } catch {
        Say "error" $_.Exception.Message
        return $false
    }
}

function Uninstall-Varedura {
    Say "uninstalling"

    $uvCmd = (Get-Command "uv" -ErrorAction SilentlyContinue).Source
    if (-not $uvCmd) {
        Say "error" "uv not found"
        return $false
    }

    try {
        $result = & $uvCmd tool uninstall $AppName 2>&1
        $exitCode = $LASTEXITCODE
        if ($result) { Write-Host ($result -join "`n") }

        if ($exitCode -ne 0) {
            Say "error" "uv tool uninstall failed"
            return $false
        }

        Say "uninstall_ok"
        return $true
    } catch {
        Say "error" $_.Exception.Message
        return $false
    }
}

function Test-Installed {
    Refresh-InstallerPath
    return (Test-CmdAvailable $AppName)
}

# ═══════════════════════════ Success Banner ═══════════════════════════════
function Print-Success {
    Write-Host ""
    Write-Host "  +------------------------------------------------+" -ForegroundColor Green
    if ($Lang -eq "pt") {
        Write-Host "  |   [+] Varedura instalado com sucesso!          |" -ForegroundColor Green
    } else {
        Write-Host "  |   [+] Varedura installed successfully!         |" -ForegroundColor Green
    }
    Write-Host "  +------------------------------------------------+" -ForegroundColor Green
    Write-Host ""
    if ($Lang -eq "pt") {
        Write-Host "   Digite " -NoNewline
        Write-Host "varedura" -ForegroundColor Cyan -NoNewline
        Write-Host " no terminal para iniciar."
    } else {
        Write-Host "   Type " -NoNewline
        Write-Host "varedura" -ForegroundColor Cyan -NoNewline
        Write-Host " in the terminal to start."
    }
    Write-Host ""
}

# ═══════════════════════════ Main Flows ═══════════════════════════════════
function Do-Check {
    $osInfo = Detect-OS
    Check-Dependencies

    if ($script:ToInstall.Count -gt 0) {
        Say "check_missing" ($script:ToInstall -join ", ")
        return $false
    }
    Say "check_ready"
    return $true
}

function Do-Uninstall {
    if (-not (Test-Installed)) {
        Say "not_installed"
        return $false
    }
    return (Uninstall-Varedura)
}

function Do-Install {
    # Already installed?
    if (Test-Installed) {
        Say "already_installed"
        $action = Ask-Action
        switch ($action) {
            "reinstall" { <# continue #> }
            "uninstall" { Uninstall-Varedura; return }
            default     { Say "abort"; return }
        }
    }

    # 1. Detect OS
    $osInfo = Detect-OS

    # 2. Check dependencies
    Check-Dependencies

    # 3. Summary
    Say "summary_hdr"
    Say "sum_os" "$($osInfo.Name) $($osInfo.Arch)"

    $installItems = @($script:ToInstall) + @($AppName)
    Say "sum_install" ($installItems -join ", ")

    if ($script:AlreadyOK.Count -gt 0) {
        Say "sum_ok" ($script:AlreadyOK -join ", ")
    }

    # 4. Confirm
    if (-not (Confirm-Yes "confirm_install")) {
        Say "abort"
        return
    }

    # 5. Install uv if needed
    if ("uv" -in $script:ToInstall) {
        $ok = Install-Uv
        if (-not $ok) { return }
    }

    # 6. Install varedura
    $ok = Install-Varedura -OsInfo $osInfo
    if (-not $ok) { return }

    # 7. Success
    Print-Success

    Refresh-InstallerPath
    if (-not (Test-CmdAvailable $AppName)) {
        $toolBin = Join-Path $env:USERPROFILE ".local\bin"
        Say "path_hint" $toolBin
        Say "restart_hint"
    }
}

# ═══════════════════════════ Entry Point ══════════════════════════════════
if ($Help) {
    Write-Host "Usage: .\install.ps1 [-Uninstall] [-Check] [-Lang pt|en]"
    exit 0
}

Print-Banner

if ($Check) {
    $result = Do-Check
    if ($result) { exit 0 } else { exit 1 }
} elseif ($Uninstall) {
    $result = Do-Uninstall
    if ($result) { exit 0 } else { exit 1 }
} else {
    Do-Install
}

