from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
from src.models.stock_opname import db, Product, StockOpnameSession, StockOpnameDetail
from sqlalchemy import func
import csv
import io
# import pandas as pd  # Commented out for deployment
from datetime import datetime
import tempfile
import os

import_export_bp = Blueprint('import_export', __name__)

@import_export_bp.route('/import/products', methods=['POST'])
@cross_origin()
def import_products():
    """Import products from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'File tidak ditemukan'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'File tidak dipilih'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'File harus berformat CSV'}), 400
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):  # Start from 2 because row 1 is header
            try:
                # Expected columns: kode_produk, nama_produk, kategori_produk
                kode_produk = row.get('kode_produk', '').strip()
                nama_produk = row.get('nama_produk', '').strip()
                kategori_produk = row.get('kategori_produk', '').strip()
                
                if not kode_produk or not nama_produk:
                    errors.append(f'Baris {row_num}: Kode produk dan nama produk wajib diisi')
                    continue
                
                # Check if product already exists
                existing_product = Product.query.filter_by(kode_produk=kode_produk).first()
                if existing_product:
                    skipped_count += 1
                    continue
                
                # Create new product
                product = Product(
                    kode_produk=kode_produk,
                    nama_produk=nama_produk,
                    kategori_produk=kategori_produk if kategori_produk else None
                )
                
                db.session.add(product)
                imported_count += 1
                
            except Exception as e:
                errors.append(f'Baris {row_num}: {str(e)}')
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Import selesai. {imported_count} produk berhasil diimpor, {skipped_count} produk dilewati',
            'data': {
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': errors
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error saat import: {str(e)}'}), 500

@import_export_bp.route('/export/products', methods=['GET'])
@cross_origin()
def export_products():
    """Export all products to CSV"""
    try:
        products = Product.query.all()
        
        # Create CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['kode_produk', 'nama_produk', 'kategori_produk'])
        
        # Write data
        for product in products:
            writer.writerow([
                product.kode_produk,
                product.nama_produk,
                product.kategori_produk or ''
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        return jsonify({
            'success': True,
            'data': {
                'csv_data': csv_data,
                'filename': f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@import_export_bp.route('/export/stock-opname/<int:session_id>/excel', methods=['GET'])
@cross_origin()
def export_stock_opname_excel(session_id):
    """Export stock opname data to CSV format (Excel functionality disabled for deployment)"""
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
        
        # Create CSV data instead of Excel
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
        
        filename = f'stock_opname_{session.lokasi}_{session.waktu_mulai.strftime("%Y%m%d_%H%M%S")}.csv'
        
        return jsonify({
            'success': True,
            'data': {
                'csv_data': csv_data,
                'filename': filename,
                'content_type': 'text/csv'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@import_export_bp.route('/template/products', methods=['GET'])
@cross_origin()
def download_product_template():
    """Download CSV template for product import"""
    try:
        # Create sample CSV template
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['kode_produk', 'nama_produk', 'kategori_produk'])
        
        # Write sample data
        writer.writerow(['P001', 'Contoh Produk 1', 'Kategori A'])
        writer.writerow(['P002', 'Contoh Produk 2', 'Kategori B'])
        
        csv_data = output.getvalue()
        output.close()
        
        return jsonify({
            'success': True,
            'data': {
                'csv_data': csv_data,
                'filename': 'template_import_produk.csv'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

