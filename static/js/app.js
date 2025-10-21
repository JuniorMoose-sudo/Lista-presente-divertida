class WeddingGiftApp {
    constructor() {
        this.initEventListeners();
    }

    initEventListeners() {
        // Botões de contribuir
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-contribuir')) {
                this.openContributionModal(e.target);
            }
        });

        // Confirmar contribuição
        document.getElementById('btnConfirmarContribuicao')?.addEventListener('click', () => {
            this.confirmContribution();
        });

        // Validação do valor em tempo real
        document.getElementById('valor')?.addEventListener('input', (e) => {
            this.validateAmount(e.target);
        });
    }

    openContributionModal(button) {
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
        document.getElementById('formContribuicao').reset();

        // Abre o modal
        const modal = new bootstrap.Modal(document.getElementById('modalContribuicao'));
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

    async confirmContribution() {
        const form = document.getElementById('formContribuicao');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const data = {
            presente_id: parseInt(formData.get('presente_id')),
            nome: formData.get('nome'),
            email: formData.get('email'),
            valor: parseFloat(formData.get('valor')),
            mensagem: formData.get('mensagem')
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
                // Fecha os modais
                bootstrap.Modal.getInstance(document.getElementById('modalContribuicao')).hide();
                this.hideLoading();

                // Redireciona para o pagamento
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