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

        // Alteração do método de pagamento
        document.querySelectorAll('input[name="metodo_pagamento"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.configurarMetodoPagamento();
            });
        });

        // REMOVIDO: Validação do valor em tempo real (não é mais necessário)
    }

    openPagamentoModal(button) {
        const presenteId = button.dataset.presenteId;
        const presenteNome = button.dataset.presenteNome;
        const valorTotal = parseFloat(button.dataset.presenteValor);

        // Valida se elementos existem antes de usar
        const nomeSpan = document.getElementById('modal-presente-nome');
        const idInput = document.getElementById('presente_id');
        const valorInput = document.getElementById('valor');
        const valorExibidoSpan = document.getElementById('valor-exibido');

        if (!nomeSpan || !idInput || !valorInput) {
            console.error('Elementos do modal não encontrados');
            return;
        }

        // Preenche o modal
        nomeSpan.textContent = presenteNome;
        idInput.value = presenteId;
        
        // Define o valor fixo do presente (não editável)
        if (valorExibidoSpan) {
            valorExibidoSpan.textContent = valorTotal.toFixed(2);
        }
        
        // Define o valor fixo no campo hidden
        valorInput.value = valorTotal.toFixed(2);

        // Limpa o formulário (exceto o valor que é fixo)
        const form = document.getElementById('formPagamento');
        if (form) {
            form.reset();
            // Restaura o valor fixo após o reset
            valorInput.value = valorTotal.toFixed(2);
        }

        // Abre o modal
        const modalEl = document.getElementById('modalPagamento');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    // REMOVIDO: validateAmount não é mais necessário

    configurarMetodoPagamento() {
        const infoPix = document.getElementById('info-pix');
        const btnPix = document.getElementById('btnPagarPix');

        // Como só temos PIX, sempre mostra os elementos do PIX
        if (infoPix) {
            infoPix.style.display = 'block';
        }
        if (btnPix) {
            btnPix.style.display = 'inline-block';
        }
    }

    async processarPix() {
        const form = document.getElementById('formPagamento');
        
        if (!form?.checkValidity()) {
            form?.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const data = {
            presente_id: parseInt(formData.get('presente_id')),
            presente_nome: document.getElementById('modal-presente-nome')?.textContent || '',
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
                const pagamentoModal = bootstrap.Modal.getInstance(document.getElementById('modalPagamento'));
                pagamentoModal?.hide();
                
                // Preenche e abre modal PIX
                const valorPixSpan = document.getElementById('valor-pix');
                if (valorPixSpan) {
                    valorPixSpan.textContent = data.valor.toFixed(2);
                }
                this.copiarChavePix();
                
                const modalPixEl = document.getElementById('modalPix');
                if (modalPixEl) {
                    const modalPix = new bootstrap.Modal(modalPixEl);
                    modalPix.show();
                }
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            this.hideLoading();
            this.showError(error.message);
        }
    }

    showLoading() {
        const modalEl = document.getElementById('modalLoading');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    hideLoading() {
        const modalEl = document.getElementById('modalLoading');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
        }
    }

    showError(message) {
        alert(`Erro: ${message}`);
    }

    showSuccess(message) {
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