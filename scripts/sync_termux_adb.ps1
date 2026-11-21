<#
.SYNOPSIS
    Sincroniza o repositorio Varedura do PC para o Termux via ADB + SSH (tar-over-SSH).

.DESCRIPTION
    Configura `adb forward tcp:<Port> tcp:8022`, empacota o repositorio local com `tar`
    excluindo caches, ambientes virtuais, artefatos gerados e arquivos privados/grandes,
    descompacta em `<RemoteDir>` no dispositivo Termux via SSH IPv4 (`127.0.0.1`), garante
    `.git` inicializado com `origin = https://github.com/joaosnet/Varedura.git` (sem token)
    e opcionalmente executa `scripts/termux_install.sh`.

.EXAMPLE
    .\scripts\sync_termux_adb.ps1 -Install -ReplaceMenu

.EXAMPLE
    .\scripts\sync_termux_adb.ps1 -Serial RQCX904E6MT -RemoteDir ~/varedura -Install
#>

[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Serial ADB do dispositivo (auto-detectado se houver apenas 1 dispositivo)")]
    [string]$Serial = "",

    [Parameter(HelpMessage = "Porta TCP local redirecionada para o sshd do Termux (8022)")]
    [ValidateRange(1, 65535)]
    [int]$Port = 8022,

    [Parameter(HelpMessage = "Diretorio destino no Termux")]
    [string]$RemoteDir = "~/varedura",

    [Parameter(HelpMessage = "Executa scripts/termux_install.sh apos sincronizar")]
    [switch]$Install,

    [Parameter(HelpMessage = "Passa --replace-menu para scripts/termux_install.sh (requer -Install)")]
    [switch]$ReplaceMenu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Evita BOM UTF-8 e corrupcao CRLF em pipes nativos no Windows PowerShell 5.1 / 7+
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

function Assert-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatorio '$Name' nao encontrado no PATH."
    }
}

function Resolve-AdbSerial {
    param([string]$RequestedSerial)

    $adbOut = & adb devices 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar 'adb devices': $($adbOut -join "`n")"
    }

    $online = @()
    foreach ($line in $adbOut) {
        if ($line -match '^([^\s]+)\s+device$') {
            $online += $Matches[1]
        }
    }

    if ($RequestedSerial) {
        if ($online -notcontains $RequestedSerial) {
            $found = if ($online.Count -gt 0) { $online -join ", " } else { "nenhum" }
            throw "Dispositivo '$RequestedSerial' nao encontrado em estado 'device'. Conectados: $found"
        }
        return $RequestedSerial
    }

    if ($online.Count -eq 0) {
        throw "Nenhum dispositivo ADB em estado 'device' encontrado. Conecte via USB e ative a depuracao USB."
    }
    if ($online.Count -gt 1) {
        throw "Multiplos dispositivos ADB encontrados ($($online -join ', ')). Informe -Serial <id>."
    }
    return $online[0]
}

function Invoke-TermuxBash {
    param(
        [Parameter(Mandatory = $true)][int]$SshPort,
        [Parameter(Mandatory = $true)][string]$ScriptBody,
        [string[]]$ScriptArgs = @(),
        [switch]$Quiet
    )

    # IMPORTANTE (OpenSSH no Windows): nunca passar '>' ou aspas duplas aninhadas nos args do ssh.
    # Sempre enviar scripts LF-only via stdin para `bash -s`.
    $sshArgs = "-4 -T -o BatchMode=yes -o ConnectTimeout=15 -p $SshPort 127.0.0.1 bash -s"
    if ($ScriptArgs.Count -gt 0) {
        foreach ($arg in $ScriptArgs) {
            if ($arg -notmatch '^[~A-Za-z0-9_./=-]+$') {
                throw "Argumento remoto inseguro ou invalido: '$arg'"
            }
        }
        $sshArgs += " -- " + ($ScriptArgs -join " ")
    }

    $lfScript = ($ScriptBody -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd("`n") + "`n"
    $scriptBytes = $Utf8NoBom.GetBytes($lfScript)

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "ssh"
    $psi.Arguments = $sshArgs
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    try {
        $proc.StandardInput.BaseStream.Write($scriptBytes, 0, $scriptBytes.Length)
        $proc.StandardInput.BaseStream.Flush()
        $proc.StandardInput.BaseStream.Close()

        $outTask = $proc.StandardOutput.ReadToEndAsync()
        $errTask = $proc.StandardError.ReadToEndAsync()
        $proc.WaitForExit()

        $stdout = $outTask.GetAwaiter().GetResult()
        $stderr = $errTask.GetAwaiter().GetResult()

        if (-not $Quiet) {
            if ($stdout) { Write-Host $stdout.TrimEnd() }
            if ($stderr) { Write-Host $stderr.TrimEnd() -ForegroundColor DarkYellow }
        }

        if ($proc.ExitCode -ne 0) {
            throw "Comando SSH falhou (exit $($proc.ExitCode)).`nSTDOUT: $stdout`nSTDERR: $stderr"
        }

        return $stdout
    } finally {
        $proc.Dispose()
    }
}

function Send-TarArchiveOverSsh {
    param(
        [Parameter(Mandatory = $true)][int]$SshPort,
        [Parameter(Mandatory = $true)][string]$LocalRepoRoot,
        [Parameter(Mandatory = $true)][string]$ResolvedRemoteDir,
        [Parameter(Mandatory = $true)][string[]]$ExcludePatterns
    )

    if ($ResolvedRemoteDir -notmatch '^/[A-Za-z0-9_./-]+$') {
        throw "Caminho remoto resolvido inesperado: '$ResolvedRemoteDir'"
    }

    $tempArchive = [System.IO.Path]::GetTempFileName() + ".tar.gz"
    try {
        $tarArgs = [System.Collections.Generic.List[string]]::new()
        $tarArgs.Add("-czf")
        $tarArgs.Add($tempArchive)
        foreach ($pattern in $ExcludePatterns) {
            $tarArgs.Add("--exclude=$pattern")
        }
        $tarArgs.Add("-C")
        $tarArgs.Add($LocalRepoRoot)
        $tarArgs.Add(".")

        & tar @tarArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao gerar arquivo tar local (exit $LASTEXITCODE)."
        }

        $archiveSize = (Get-Item $tempArchive).Length
        Write-Host "    Arquivo comprimido: $([Math]::Round($archiveSize / 1KB, 1)) KB"

        $psi = [System.Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = "ssh"
        $psi.Arguments = "-4 -T -o BatchMode=yes -o ConnectTimeout=15 -p $SshPort 127.0.0.1 tar --warning=no-unknown-keyword -xzf - -C $ResolvedRemoteDir"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardInput = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        try {
            $fileStream = [System.IO.File]::OpenRead($tempArchive)
            try {
                $fileStream.CopyTo($proc.StandardInput.BaseStream)
            } finally {
                $fileStream.Dispose()
            }
            $proc.StandardInput.BaseStream.Flush()
            $proc.StandardInput.BaseStream.Close()

            $outTask = $proc.StandardOutput.ReadToEndAsync()
            $errTask = $proc.StandardError.ReadToEndAsync()
            $proc.WaitForExit()

            $stdout = $outTask.GetAwaiter().GetResult()
            $stderr = $errTask.GetAwaiter().GetResult()
            if ($stdout) { Write-Host $stdout.TrimEnd() }
            if ($stderr) { Write-Host $stderr.TrimEnd() -ForegroundColor DarkYellow }

            if ($proc.ExitCode -ne 0) {
                throw "Extracao tar-over-SSH falhou (exit $($proc.ExitCode)).`n$stderr"
            }
        } finally {
            $proc.Dispose()
        }
    } finally {
        Remove-Item -LiteralPath $tempArchive -Force -ErrorAction SilentlyContinue
    }
}

# ── Validacoes iniciais ─────────────────────────────────────────────────────
Assert-CommandAvailable -Name "adb"
Assert-CommandAvailable -Name "ssh"
Assert-CommandAvailable -Name "tar"

if ($RemoteDir -notmatch '^[~A-Za-z0-9_./-]+$') {
    throw "RemoteDir invalido '$RemoteDir'. Use apenas letras, numeros, '/', '_', '-', '.' e prefixo '~/'."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "pyproject.toml nao encontrado em '$RepoRoot'. Execute a partir do repositorio Varedura."
}

if ($ReplaceMenu -and -not $Install) {
    Write-Warning "-ReplaceMenu tem efeito somente quando combinado com -Install."
}

# ── 1. ADB serial + port forward ────────────────────────────────────────────
$TargetSerial = Resolve-AdbSerial -RequestedSerial $Serial
Write-Host "==> [1/4] Conectando ao dispositivo ADB '$TargetSerial' (porta $Port -> 8022)..."
& adb -s $TargetSerial forward "tcp:$Port" "tcp:8022" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao executar 'adb -s $TargetSerial forward tcp:$Port tcp:8022'."
}

# ── 2. Resolver e criar diretorio remoto ────────────────────────────────────
Write-Host "==> [2/4] Preparando diretorio remoto '$RemoteDir'..."
$resolveScript = @'
set -euo pipefail
TARGET_DIR="$1"
case "$TARGET_DIR" in
    "~") TARGET_DIR="$HOME" ;;
    "~/"*) TARGET_DIR="$HOME/${TARGET_DIR#~/}" ;;
esac
mkdir -p "$TARGET_DIR"
printf 'RESOLVED_DIR=%s\n' "$TARGET_DIR"
'@

$resolveOut = Invoke-TermuxBash -SshPort $Port -ScriptBody $resolveScript -ScriptArgs @($RemoteDir) -Quiet
$resolvedLine = ($resolveOut -split "`r?`n" | Where-Object { $_ -like "RESOLVED_DIR=*" } | Select-Object -Last 1)
if (-not $resolvedLine) {
    throw "Nao foi possivel resolver o diretorio remoto '$RemoteDir'. Saida:`n$resolveOut"
}
$ResolvedRemoteDir = $resolvedLine.Substring("RESOLVED_DIR=".Length).Trim()
Write-Host "    Destino resolvido: $ResolvedRemoteDir"

# ── 3. Sincronizar arquivos via tar-over-SSH ────────────────────────────────
Write-Host "==> [3/4] Enviando arquivos para o Termux via tar-over-SSH..."
$Excludes = @(
    ".venv",
    ".git",
    "__pycache__",
    "logs",
    "exports",
    "runtime",
    "screenshots",
    "graphify-out",
    "lmarena",
    "build",
    "dist",
    "*.egg-info",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    ".coverage.*",
    "credenciais.json",
    "ips_conhecidos.json",
    "regioes.json",
    "camera_bridge_state.json",
    ".camera-locations.private.json",
    "roteador_creds.txt",
    "router_template.html",
    "todos_ips_belem.txt"
)

Send-TarArchiveOverSsh `
    -SshPort $Port `
    -LocalRepoRoot $RepoRoot `
    -ResolvedRemoteDir $ResolvedRemoteDir `
    -ExcludePatterns $Excludes

# ── 4. Inicializar .git (sem token) e rodar instalador se solicitado ────────
Write-Host "==> [4/4] Finalizando Git remoto e permissao de scripts..."
$postSyncScript = @'
set -euo pipefail
TARGET_DIR="$1"
DO_INSTALL="$2"
DO_REPLACE_MENU="$3"

if [ -d "$TARGET_DIR/scripts" ]; then
    for sh_file in "$TARGET_DIR/scripts/"*.sh; do
        [ -f "$sh_file" ] || continue
        tr -d '\r' < "$sh_file" > "$sh_file.tmp" && mv "$sh_file.tmp" "$sh_file"
        chmod 0755 "$sh_file"
    done
fi

if command -v git >/dev/null 2>&1; then
    if [ ! -d "$TARGET_DIR/.git" ]; then
        git -C "$TARGET_DIR" init -q
        git -C "$TARGET_DIR" symbolic-ref HEAD refs/heads/main
        git -C "$TARGET_DIR" remote add origin https://github.com/joaosnet/Varedura.git
        git -C "$TARGET_DIR" fetch --depth 1 --quiet origin main >/dev/null 2>&1 || true
        if git -C "$TARGET_DIR" rev-parse --verify FETCH_HEAD >/dev/null 2>&1; then
            git -C "$TARGET_DIR" reset --soft FETCH_HEAD >/dev/null 2>&1 || true
        fi
    elif ! git -C "$TARGET_DIR" remote get-url origin >/dev/null 2>&1; then
        git -C "$TARGET_DIR" remote add origin https://github.com/joaosnet/Varedura.git
    fi

    git -C "$TARGET_DIR" add -A
    if ! git -C "$TARGET_DIR" diff --cached --quiet; then
        git -C "$TARGET_DIR" -c user.name=Varedura -c user.email=varedura@local commit -q -m "chore(sync): ADB sync snapshot"
    fi
else
    echo "Aviso: git ainda nao instalado no Termux; inicializacao de .git adiada."
fi

if [ "$DO_INSTALL" = "1" ]; then
    INSTALL_ARGS=(--repo-dir "$TARGET_DIR")
    if [ "$DO_REPLACE_MENU" = "1" ]; then
        INSTALL_ARGS+=(--replace-menu)
    fi
    bash "$TARGET_DIR/scripts/termux_install.sh" "${INSTALL_ARGS[@]}"
fi
'@

$doInstallArg = if ($Install) { "1" } else { "0" }
$doReplaceArg = if ($ReplaceMenu) { "1" } else { "0" }

Invoke-TermuxBash `
    -SshPort $Port `
    -ScriptBody $postSyncScript `
    -ScriptArgs @($ResolvedRemoteDir, $doInstallArg, $doReplaceArg) | Out-Null

Write-Host ""
Write-Host "Sincronizacao concluida para '$ResolvedRemoteDir' no dispositivo '$TargetSerial'." -ForegroundColor Green
if (-not $Install) {
    Write-Host "Para instalar dependencias e o pacote editavel no Termux, rode:"
    Write-Host "  .\scripts\sync_termux_adb.ps1 -Serial $TargetSerial -Port $Port -RemoteDir $RemoteDir -Install"
}
