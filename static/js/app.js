class WeddingGiftApp {
    constructor() {
        this.initEventListeners();
        this.configurarMetodoPagamento();
    }

    initEventListeners() {
        // Botões de contribuir
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-presentear')) {
                this.openPagamentoModal(e.target);
            }
        });

        // Botão Pagar com PIX
        document.getElementById('btnPagarPix')?.addEventListener('click', () => {
            this.processarPix();
        });

        // Botão Pagar com Cartão
        document.getElementById('btnPagarCartao')?.addEventListener('click', () => {
            this.processarCartao();
        });

        // Alteração do método de pagamento
        document.querySelectorAll('input[name="metodo_pagamento"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.configurarMetodoPagamento();
            });
        });

        // Validação do valor em tempo real
        document.getElementById('valor')?.addEventListener('input', (e) => {
            this.validateAmount(e.target);
        });
    }

    openPagamentoModal(button) {
        const presenteId = button.dataset.presenteId;
        const presenteNome = button.dataset.presenteNome;
        const valorRestante = parseFloat(button.dataset.valorRestante);

        // Preenche o modal
        document.getElementById('modal-presente-nome').textContent = presenteNome;
        document.getElementById('presente_id').value = presenteId;
        document.getElementById('valor-maximo').textContent = valorRestante.toFixed(2);
        
        // Define o valor máximo
        document.getElementById('valor').max = valorRestante;
        document.getElementById('valor').value = '';

        // Limpa o formulário
        document.getElementById('formPagamento').reset();

        // Abre o modal
        const modal = new bootstrap.Modal(document.getElementById('modalPagamento'));
        modal.show();
    }

    validateAmount(input) {
        const maxValue = parseFloat(input.max);
        const currentValue = parseFloat(input.value) || 0;

        if (currentValue > maxValue) {
            input.setCustomValidity(`Valor máximo: R$ ${maxValue.toFixed(2)}`);
            input.reportValidity();
        } else {
            input.setCustomValidity('');
        }
    }

    configurarMetodoPagamento() {
        const metodo = document.querySelector('input[name="metodo_pagamento"]:checked')?.value;
        const infoPix = document.getElementById('info-pix');
        const btnPix = document.getElementById('btnPagarPix');
        const btnCartao = document.getElementById('btnPagarCartao');

        if (metodo === 'pix') {
            infoPix.style.display = 'block';
            btnPix.style.display = 'inline-block';
            btnCartao.style.display = 'none';
        } else {
            infoPix.style.display = 'none';
            btnPix.style.display = 'none';
            btnCartao.style.display = 'inline-block';
        }
    }

    async processarPix() {
        const form = document.getElementById('formPagamento');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const data = {
            presente_id: parseInt(formData.get('presente_id')),
            presente_nome: document.getElementById('modal-presente-nome').textContent,
            nome: formData.get('nome'),
            email: formData.get('email'),
            cpf: formData.get('cpf'),
            telefone: formData.get('telefone'),
            valor: parseFloat(formData.get('valor')),
            mensagem: formData.get('mensagem'),
            metodo_pagamento: 'pix'
        };

        try {
            // Mostra loading
            this.showLoading();

            const response = await fetch('/api/contribuir', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.hideLoading();
                // Fecha o modal de pagamento
                bootstrap.Modal.getInstance(document.getElementById('modalPagamento')).hide();
                
                // Preenche e abre modal PIX
                document.getElementById('valor-pix').textContent = data.valor.toFixed(2);
                this.copiarChavePix();
                
                const modalPix = new bootstrap.Modal(document.getElementById('modalPix'));
                modalPix.show();
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.hideLoading();
            this.showError(error.message);
        }
    }

    async processarCartao() {
        const form = document.getElementById('formPagamento');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const data = {
            presente_id: parseInt(formData.get('presente_id')),
            presente_nome: document.getElementById('modal-presente-nome').textContent,
            nome: formData.get('nome'),
            email: formData.get('email'),
            cpf: formData.get('cpf'),
            telefone: formData.get('telefone'),
            valor: parseFloat(formData.get('valor')),
            mensagem: formData.get('mensagem'),
            metodo_pagamento: 'cartao'
        };

        try {
            // Mostra loading
            this.showLoading();

            const response = await fetch('/api/contribuir', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                    // Garantir que o loading foi escondido e modal fechado
                    try { this.hideLoading(); } catch (e) { console.warn('hideLoading failed', e); }
                    try { bootstrap.Modal.getInstance(document.getElementById('modalPagamento'))?.hide(); } catch (e) { /* ignore */ }

                    console.log('Payment response (cartao):', result);
                    if (!result.payment_url) {
                        this.showError('Não foi possível gerar o link de pagamento. Tente novamente mais tarde.');
                        return;
                    }

                    // Redireciona para Mercado Pago
                    console.log('Redirecionando para:', result.payment_url);
                    window.location.href = result.payment_url;
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.hideLoading();
            this.showError(error.message);
        }
    }

    showLoading() {
        const modal = new bootstrap.Modal(document.getElementById('modalLoading'));
        modal.show();
    }

    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalLoading'));
        modal?.hide();
    }

    showError(message) {
        alert(`Erro: ${message}`);
    }

    showSuccess(message) {
        // Poderia usar um toast mais elaborado aqui
        alert(message);
    }

    copiarChavePix() {
        const chavePix = '83991314075';
        navigator.clipboard.writeText(chavePix).then(() => {
            console.log('Chave PIX copiada: ' + chavePix);
        }).catch(err => {
            console.error('Erro ao copiar: ', err);
        });
    }
}

// Inicializa a aplicação quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    new WeddingGiftApp();
});

// Função para atualizar a lista de presentes (opcional, para atualizações em tempo real)
async function atualizarListaPresentes() {
    try {
        const response = await fetch('/api/presentes');
        const result = await response.json();
        
        if (result.success) {
            // Aqui você poderia atualizar a UI com os novos dados
            console.log('Lista de presentes atualizada:', result.presentes);
        }
    } catch (error) {
        console.error('Erro ao atualizar lista:', error);
    }
}

// Atualiza a lista a cada 30 segundos (opcional)
// setInterval(atualizarListaPresentes, 30000);