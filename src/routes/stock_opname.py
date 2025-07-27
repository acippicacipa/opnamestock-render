from flask import Blueprint, request, jsonify
from src.models.stock_opname import db, Product, StockOpnameSession, StockOpnameDetail
from datetime import datetime
from sqlalchemy import or_

stock_opname_bp = Blueprint('stock_opname', __name__)

# Product routes
@stock_opname_bp.route('/products', methods=['GET'])
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        query = Product.query
        
        if search:
            query = query.filter(
                or_(
                    Product.nama_produk.contains(search),
                    Product.kode_produk.contains(search),
                    Product.saldo_awal.contains(search)
                )
            )
        
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [product.to_dict() for product in products.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': products.total,
                'pages': products.pages
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/products', methods=['POST'])
def create_product():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['kode_produk', 'nama_produk', 'saldo_awal']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Check if product code already exists
        existing_product = Product.query.filter_by(kode_produk=data['kode_produk']).first()
        if existing_product:
            return jsonify({'success': False, 'message': 'Kode produk sudah ada'}), 400
        
        product = Product(
            kode_produk=data['kode_produk'],
            nama_produk=data['nama_produk'],
            saldo_awal=data['saldo_awal']
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Produk berhasil ditambahkan',
            'data': product.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/products/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('q', '', type=str)
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'success': True, 'data': []})
        
        products = Product.query.filter(
            or_(
                Product.nama_produk.contains(query),
                Product.kode_produk.contains(query)
            )
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [product.to_dict() for product in products]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Session routes
@stock_opname_bp.route('/sessions', methods=['GET'])
def get_sessions():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        sessions = StockOpnameSession.query.order_by(
            StockOpnameSession.waktu_mulai.desc()
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [session.to_dict() for session in sessions.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': sessions.total,
                'pages': sessions.pages
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions', methods=['POST'])
def create_session():
    try:
        data = request.get_json()
        
        if 'lokasi' not in data or not data['lokasi']:
            return jsonify({'success': False, 'message': 'Lokasi is required'}), 400
        
        session = StockOpnameSession(
            lokasi=data['lokasi'],
            created_by=data.get('created_by', 'system')
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sesi stock opname berhasil dibuat',
            'data': session.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions/<int:session_id>/complete', methods=['PUT'])
def complete_session(session_id):
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        
        if session.status == 'completed':
            return jsonify({'success': False, 'message': 'Sesi sudah selesai'}), 400
        
        session.status = 'completed'
        session.waktu_selesai = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sesi stock opname berhasil diselesaikan',
            'data': session.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Detail routes
@stock_opname_bp.route('/sessions/<int:session_id>/details', methods=['GET'])
def get_session_details(session_id):
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        
        details = StockOpnameDetail.query.filter_by(session_id=session_id).all()
        
        return jsonify({
            'success': True,
            'session': session.to_dict(),
            'data': [detail.to_dict() for detail in details]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions/<int:session_id>/details', methods=['POST'])
def add_session_detail(session_id):
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        
        if session.status == 'completed':
            return jsonify({'success': False, 'message': 'Sesi sudah selesai'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['product_id', 'jumlah_barang']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Check if product exists
        product = Product.query.get(data['product_id'])
        if not product:
            return jsonify({'success': False, 'message': 'Produk tidak ditemukan'}), 404
        
        # Check if detail already exists for this product in this session
        existing_detail = StockOpnameDetail.query.filter_by(
            session_id=session_id,
            product_id=data['product_id']
        ).first()
        
        if existing_detail:
            # Update existing detail
            existing_detail.jumlah_barang = data['jumlah_barang']
            existing_detail.catatan = data.get('catatan', '')
            existing_detail.updated_at = datetime.utcnow()
            detail = existing_detail
        else:
            # Create new detail
            detail = StockOpnameDetail(
                session_id=session_id,
                product_id=data['product_id'],
                jumlah_barang=data['jumlah_barang'],
                catatan=data.get('catatan', '')
            )
            db.session.add(detail)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Data berhasil direkam',
            'data': detail.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500