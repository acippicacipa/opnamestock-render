from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.stock_opname import db, Product, StockOpnameSession, StockOpnameDetail
from datetime import datetime
from sqlalchemy import or_, func
import csv
import io

stock_opname_bp = Blueprint('stock_opname', __name__)

# Product endpoints
@stock_opname_bp.route('/products', methods=['GET'])
@cross_origin()
def get_products():
    """Get all products with optional search"""
    try:
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        query = Product.query
        
        if search:
            query = query.filter(
                or_(
                    Product.nama_produk.ilike(f'%{search}%'),
                    Product.kode_produk.ilike(f'%{search}%'),
                    Product.kategori_produk.ilike(f'%{search}%')
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

@stock_opname_bp.route('/products/search', methods=['GET'])
@cross_origin()
def search_products():
    """Search products by keyword for stock opname"""
    try:
        keyword = request.args.get('keyword', '')
        limit = int(request.args.get('limit', 5))
        
        if not keyword:
            return jsonify({'success': True, 'data': []})
        
        products = Product.query.filter(
            or_(
                Product.nama_produk.ilike(f'%{keyword}%'),
                Product.kode_produk.ilike(f'%{keyword}%')
            )
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [product.to_dict() for product in products]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/products', methods=['POST'])
@cross_origin()
def create_product():
    """Create a new product"""
    try:
        data = request.get_json()
        
        # Check if product code already exists
        existing_product = Product.query.filter_by(kode_produk=data['kode_produk']).first()
        if existing_product:
            return jsonify({'success': False, 'message': 'Kode produk sudah ada'}), 400
        
        product = Product(
            kode_produk=data['kode_produk'],
            nama_produk=data['nama_produk'],
            kategori_produk=data.get('kategori_produk')
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

@stock_opname_bp.route('/products/delete-all', methods=['DELETE'])
@cross_origin()
def delete_all_products():
    """Delete all products"""
    try:
        # Check if there are any active stock opname sessions
        active_sessions = StockOpnameSession.query.filter_by(status='active').count()
        if active_sessions > 0:
            return jsonify({
                'success': False, 
                'message': 'Tidak dapat menghapus produk karena ada sesi stock opname yang sedang aktif'
            }), 400
        
        # Delete all stock opname details first (due to foreign key constraints)
        StockOpnameDetail.query.delete()
        
        # Delete all products
        deleted_count = Product.query.count()
        Product.query.delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Berhasil menghapus {deleted_count} produk',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Stock Opname Session endpoints
@stock_opname_bp.route('/sessions', methods=['GET'])
@cross_origin()
def get_sessions():
    """Get all stock opname sessions"""
    try:
        sessions = StockOpnameSession.query.order_by(StockOpnameSession.waktu_mulai.desc()).all()
        return jsonify({
            'success': True,
            'data': [session.to_dict() for session in sessions]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions', methods=['POST'])
@cross_origin()
def start_session():
    """Start a new stock opname session"""
    try:
        data = request.get_json()
        
        session = StockOpnameSession(
            lokasi=data['lokasi'],
            created_by=data.get('created_by', 'Admin')
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sesi stock opname berhasil dimulai',
            'data': session.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions/<int:session_id>/complete', methods=['PUT'])
@cross_origin()
def complete_session(session_id):
    """Complete a stock opname session"""
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

# Stock Opname Detail endpoints
@stock_opname_bp.route('/sessions/<int:session_id>/details', methods=['GET'])
@cross_origin()
def get_session_details(session_id):
    """Get all details for a specific session"""
    try:
        details = StockOpnameDetail.query.filter_by(session_id=session_id).all()
        return jsonify({
            'success': True,
            'data': [detail.to_dict() for detail in details]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions/<int:session_id>/details', methods=['POST'])
@cross_origin()
def add_detail():
    """Add or update stock opname detail"""
    try:
        session_id = request.view_args['session_id']
        data = request.get_json()
        
        # Check if session exists and is active
        session = StockOpnameSession.query.get_or_404(session_id)
        if session.status != 'active':
            return jsonify({'success': False, 'message': 'Sesi tidak aktif'}), 400
        
        # Check if detail already exists for this product in this session
        existing_detail = StockOpnameDetail.query.filter_by(
            session_id=session_id,
            product_id=data['product_id']
        ).first()
        
        if existing_detail:
            # Update existing detail
            existing_detail.jumlah_barang = data['jumlah_barang']
            existing_detail.catatan = data.get('catatan')
            existing_detail.updated_at = datetime.utcnow()
            detail = existing_detail
        else:
            # Create new detail
            detail = StockOpnameDetail(
                session_id=session_id,
                product_id=data['product_id'],
                jumlah_barang=data['jumlah_barang'],
                catatan=data.get('catatan')
            )
            db.session.add(detail)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Data berhasil direkam',
            'data': detail.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@stock_opname_bp.route('/sessions/<int:session_id>/export', methods=['GET'])
@cross_origin()
def export_session_data(session_id):
    """Export session data to CSV format"""
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        
        # Get aggregated data (sum by product name)
        results = db.session.query(
            Product.kode_produk,
            Product.nama_produk,
            Product.kategori_produk,
            func.sum(StockOpnameDetail.jumlah_barang).label('total_qty')
        ).join(
            StockOpnameDetail, Product.id == StockOpnameDetail.product_id
        ).filter(
            StockOpnameDetail.session_id == session_id
        ).group_by(
            Product.nama_produk, Product.kode_produk, Product.kategori_produk
        ).all()
        
        # Create CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Kode Produk', 'Nama Produk', 'Kategori', 'Total Jumlah',
            'Lokasi', 'Tanggal Mulai', 'Tanggal Selesai'
        ])
        
        # Write data
        for result in results:
            writer.writerow([
                result.kode_produk,
                result.nama_produk,
                result.kategori_produk or '',
                result.total_qty,
                session.lokasi,
                session.waktu_mulai.strftime('%Y-%m-%d %H:%M:%S') if session.waktu_mulai else '',
                session.waktu_selesai.strftime('%Y-%m-%d %H:%M:%S') if session.waktu_selesai else ''
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        return jsonify({
            'success': True,
            'data': {
                'csv_data': csv_data,
                'filename': f'stock_opname_{session.lokasi}_{session.waktu_mulai.strftime("%Y%m%d_%H%M%S")}.csv'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

