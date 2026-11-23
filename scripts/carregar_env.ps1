# Lê o arquivo .env e cria uma variável de ambiente para cada linha CHAVE=valor.
# As variáveis valem só para o terminal atual (some quando você fecha o terminal).
#
# Uso, na pasta do projeto:
#     .\scripts\carregar_env.ps1

Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        $nome = $matches[1].Trim()
        $valor = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($nome, $valor, 'Process')
    }
}
Write-Host "Variaveis do .env carregadas neste terminal."
