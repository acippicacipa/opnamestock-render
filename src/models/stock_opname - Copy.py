from src.models.user import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    kode_produk = db.Column(db.String(50), unique=True, nullable=False)
    nama_produk = db.Column(db.String(200), nullable=False)
    kategori_produk = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'kode_produk': self.kode_produk,
            'nama_produk': self.nama_produk,
            'kategori_produk': self.kategori_produk,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class StockOpnameSession(db.Model):
    __tablename__ = 'stock_opname_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    lokasi = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed
    created_by = db.Column(db.String(100), default='Admin')
    waktu_mulai = db.Column(db.DateTime, default=datetime.utcnow)
    waktu_selesai = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    details = db.relationship('StockOpnameDetail', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'lokasi': self.lokasi,
            'status': self.status,
            'created_by': self.created_by,
            'waktu_mulai': self.waktu_mulai.isoformat() if self.waktu_mulai else None,
            'waktu_selesai': self.waktu_selesai.isoformat() if self.waktu_selesai else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'total_items': len(self.details) if self.details else 0
        }

class StockOpnameDetail(db.Model):
    __tablename__ = 'stock_opname_details'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('stock_opname_sessions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    jumlah_barang = db.Column(db.Integer, nullable=False)
    catatan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='stock_details', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'product_id': self.product_id,
            'product': self.product.to_dict() if self.product else None,
            'jumlah_barang': self.jumlah_barang,
            'catatan': self.catatan,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

