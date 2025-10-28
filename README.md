# Lista de Casamento - Integração com Mercado Pago

Este projeto implementa uma lista de presentes de casamento com integração ao Mercado Pago para processamento de pagamentos.

## Configuração do Ambiente

### Variáveis de Ambiente

As seguintes variáveis de ambiente são necessárias para a integração com o Mercado Pago:

```
# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=seu_access_token_aqui
MERCADOPAGO_WEBHOOK_SECRET=sua_chave_secreta_para_webhooks
MERCADOPAGO_WEBHOOK_URL=https://seu-site.com/webhook/mercadopago

# URLs de Produção
SITE_URL=https://seu-site.com
```

### Obtenção das Credenciais do Mercado Pago

1. Crie uma conta no [Mercado Pago](https://www.mercadopago.com.br/)
2. Acesse o [Painel de Desenvolvedores](https://www.mercadopago.com.br/developers/panel)
3. Crie uma aplicação para obter as credenciais
4. Copie o Access Token para a variável `MERCADOPAGO_ACCESS_TOKEN`
5. Gere uma chave secreta para webhooks e defina na variável `MERCADOPAGO_WEBHOOK_SECRET`

## Fluxo de Integração

### 1. Criação de Preferência de Pagamento

Quando um cliente finaliza uma contribuição, o sistema:

1. Valida os dados da contribuição
2. Cria um registro de contribuição no banco de dados com status "pendente"
3. Cria uma preferência de pagamento no Mercado Pago
4. Redireciona o cliente para o Checkout Pro do Mercado Pago

### 2. Processamento de Pagamento

O Mercado Pago processa o pagamento e:

1. Redireciona o cliente de volta para a aplicação (success, failure ou pending)
2. Envia notificações via webhook para atualizar o status do pagamento

### 3. Webhooks e Notificações

A aplicação recebe notificações do Mercado Pago através do endpoint `/webhook/mercadopago` e:

1. Valida a assinatura do webhook usando `MERCADOPAGO_WEBHOOK_SECRET`
2. Processa a notificação e atualiza o status da contribuição
3. Atualiza o valor arrecadado do presente se o pagamento for aprovado

## Estrutura do Código

### Serviços

- `MercadoPagoService`: Gerencia a integração com a API do Mercado Pago
  - `criar_preferencia_pagamento`: Cria uma preferência de pagamento
  - `processar_webhook`: Processa webhooks do Mercado Pago
  - `consultar_pagamento`: Consulta informações de um pagamento
  - `consultar_merchant_order`: Consulta informações de uma ordem

### Rotas

- `/api/contribuir`: Endpoint para criar uma contribuição e iniciar o fluxo de pagamento
- `/webhook/mercadopago`: Endpoint para receber notificações do Mercado Pago
- `/obrigado`, `/erro`, `/pendente`: Páginas de retorno após o pagamento

## Tratamento de Erros

A integração implementa as seguintes estratégias de tratamento de erros:

1. **Retry Mechanism**: Tentativas automáticas em caso de falhas temporárias
2. **Validação de Assinatura**: Verificação da autenticidade das notificações
3. **Processamento Idempotente**: Evita processamento duplicado de notificações
4. **Logging Detalhado**: Registra informações para debugging e monitoramento

## Testes e Depuração

### Testando a Integração

Para testar a integração com o Mercado Pago:

1. Configure as variáveis de ambiente com credenciais de teste
2. Acesse `/api/test-mp-credentials` para verificar se as credenciais estão corretas
3. Faça uma contribuição de teste e verifique o fluxo completo

### Depuração de Webhooks

Para depurar webhooks:

1. Use o [Webhook Tester](https://webhook.site/) para capturar e analisar webhooks
2. Configure temporariamente `MERCADOPAGO_WEBHOOK_URL` para apontar para o Webhook Tester
3. Verifique os logs da aplicação para informações detalhadas sobre o processamento

## Segurança

A integração implementa as seguintes práticas de segurança:

1. **Variáveis de Ambiente**: Credenciais armazenadas em variáveis de ambiente
2. **Validação de Assinatura**: Verificação da autenticidade das notificações
3. **Rate Limiting**: Limitação de requisições para evitar abusos
4. **Validação de Dados**: Validação rigorosa dos dados de entrada

## Considerações para Produção

Ao implantar em produção:

1. Certifique-se de que todas as variáveis de ambiente estão configuradas corretamente
2. Configure o domínio no painel do Mercado Pago para receber webhooks
3. Implemente monitoramento para detectar problemas rapidamente
4. Configure alertas para falhas de pagamento ou erros críticos