param()

Write-Host "Bootstrap de produção: copiando .env.example -> .env (se não existir)"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $root

if (Test-Path -LiteralPath .env) {
    Write-Host ".env já existe — operação cancelada." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path -LiteralPath .env.example)) {
    Write-Error ".env.example não encontrado. Execute este script a partir da raiz do repositório."
    exit 1
}

Copy-Item -LiteralPath .env.example -Destination .env
# Tentar definir permissão restrita no Windows (se possível)
try {
    icacls .env /inheritance:r /grant:r "%USERNAME%:R" | Out-Null
} catch {
    # ignore
}

Write-Host ".env criado a partir de .env.example. Preencha SECRET_KEY e senhas e não commite este arquivo." -ForegroundColor Green
