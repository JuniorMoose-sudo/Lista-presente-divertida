"""
Serviço de validação para contribuições e pagamentos
"""
from decimal import Decimal
from datetime import datetime, timedelta
from models.contribuicao import Contribuicao
from models.presente import Presente
from database import db

class ValidationService:
    @staticmethod
    def validar_contribuicao(presente_id, valor, email):
        """Valida se uma contribuição pode ser realizada"""
        errors = []
        
        # 1. Verifica se o presente existe e está ativo
        presente = Presente.query.get(presente_id)
        if not presente:
            errors.append("Presente não encontrado")
        elif not presente.ativo:
            errors.append("Este presente não está mais disponível")
            
        if presente:
            # 2. Verifica apenas valor mínimo
            valor_decimal = Decimal(str(valor))
            if valor_decimal < Decimal('5.00'):
                errors.append("Valor mínimo de contribuição: R$ 5,00")
        
        # 3. Verifica limite de tentativas por email (para evitar spam)
        if email:
            agora = datetime.utcnow()
            inicio_janela = agora - timedelta(minutes=5)  # Reduzido para 5 minutos
            
            tentativas = Contribuicao.query.filter(
                Contribuicao.email_contribuinte == email,
                Contribuicao.created_at >= inicio_janela
            ).count()
            
            if tentativas >= 5:
                errors.append("Muitas tentativas em um curto período. Tente novamente em 5 minutos")
        
        return errors
    
    @staticmethod
    def verificar_duplicidade(payment_id):
        """Verifica se um pagamento já foi processado"""
        return Contribuicao.query.filter_by(payment_id=payment_id).first() is not None
    
    @staticmethod
    def verificar_valor_maximo_diario(email):
        """Verifica se o usuário não excedeu o limite diário"""
        # Como queremos permitir contribuições múltiplas, removemos o limite diário
        return False
    
    @staticmethod
    def validar_presente_disponivel(presente_id):
        """Verifica se o presente ainda está disponível para contribuição"""
        presente = Presente.query.get(presente_id)
        if not presente:
            return False, "Presente não encontrado"
            
        if not presente.ativo:
            return False, "Este presente não está mais disponível"
            
        # Removida a validação de presente completo para permitir múltiplas contribuições
        return True, None