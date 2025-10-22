# Script de teste para /api/contribuir
# Envia duas requisições: com CPF e sem CPF
param(
    [string]$Host = "http://localhost:5000"
)

function Post-Contribuicao($payload) {
    $url = "$Host/api/contribuir"
    Write-Host "POST $url`nPayload: $($payload | ConvertTo-Json -Depth 5)" -ForegroundColor Cyan
    $resp = Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 5) -ErrorAction Stop
    Write-Host "Response:`n$($resp | ConvertTo-Json -Depth 5)" -ForegroundColor Green
}

# Payload com CPF
$payloadComCpf = @{
    presente_id = 1
    nome = 'Teste Com CPF'
    email = 'teste+cpf@example.com'
    cpf = '123.456.789-09'
    telefone = '(11) 99999-9999'
    valor = 2.00
    mensagem = 'Teste com CPF'
    metodo_pagamento = 'cartao'
}

# Payload sem CPF
$payloadSemCpf = @{
    presente_id = 1
    nome = 'Teste Sem CPF'
    email = 'teste+semcpf@example.com'
    # cpf ausente
    telefone = '(11) 98888-8888'
    valor = 2.00
    mensagem = 'Teste sem CPF'
    metodo_pagamento = 'cartao'
}

try {
    Post-Contribuicao -payload $payloadComCpf
} catch {
    Write-Host "Erro ao enviar payload com CPF: $_" -ForegroundColor Red
}

Start-Sleep -Seconds 1

try {
    Post-Contribuicao -payload $payloadSemCpf
} catch {
    Write-Host "Erro ao enviar payload sem CPF: $_" -ForegroundColor Red
}

Write-Host "Teste concluído. Ajuste o parâmetro -Host se necessário."
