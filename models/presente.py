from database import db
from datetime import datetime

class Presente(db.Model):
    __tablename__ = 'presentes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(500), nullable=False) 
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)  
    valor_arrecadado = db.Column(db.Numeric(10, 2), default=0.0)  
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    imagem_url = db.Column(db.String(300), default='/static/images/gift-default.jpg')
    
    contribuicoes = db.relationship('Contribuicao', backref='presente', lazy=True, cascade='all, delete-orphan')
    
    @property
    def progresso_porcentagem(self):
        if self.valor_total == 0:
            return 0
        return min(100, (float(self.valor_arrecadado) / float(self.valor_total)) * 100)
    
    @property
    def esta_completo(self):
        return float(self.valor_arrecadado) >= float(self.valor_total)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'valor_total': float(self.valor_total),
            'valor_arrecadado': float(self.valor_arrecadado),
            'progresso_porcentagem': self.progresso_porcentagem,
            'esta_completo': self.esta_completo,
            'imagem_url': self.imagem_url
        }