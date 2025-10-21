from database import db
from datetime import datetime

class Contribuicao(db.Model):
    __tablename__ = 'contribuicoes'
    
    id = db.Column(db.Integer, primary_key=True)
    presente_id = db.Column(db.Integer, db.ForeignKey('presentes.id'), nullable=False)
    nome_contribuinte = db.Column(db.String(100), nullable=False)
    email_contribuinte = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)  # Mudei de Float para Numeric
    mensagem = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendente')
    payment_id = db.Column(db.String(100))
    metodo_pagamento = db.Column(db.String(20), default='cartao')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'presente_id': self.presente_id,
            'nome_contribuinte': self.nome_contribuinte,
            'valor': float(self.valor),
            'mensagem': self.mensagem,
            'status': self.status,
            'metodo_pagamento': self.metodo_pagamento,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }