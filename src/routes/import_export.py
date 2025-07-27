from flask import Blueprint, request, jsonify, send_file, make_response
from src.models.stock_opname import db, Product, StockOpnameSession, StockOpnameDetail
from openpyxl import Workbook
import csv
import io
import pandas as pd
from datetime import datetime
import os

import_export_bp = Blueprint('import_export', __name__)

@import_export_bp.route("/import/products", methods=["POST"])
def import_products():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400

        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return jsonify({'success': False, 'message': 'File must be Excel format (.xlsx or .xls)'}), 400

        df = pd.read_excel(file)

        success_count = 0
        update_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            row_num = index + 2  # For 1-based indexing and header row
            try:
                kode_produk = str(row['Kode']).strip()
                nama_produk = str(row['Nama Barang']).strip()
                saldo_awal = int(row['Jumlah'])

                if not all([kode_produk, nama_produk, saldo_awal is not None]):
                    errors.append(f"Row {row_num}: Missing or empty required fields (kode_produk, nama_produk, saldo_awal)")
                    error_count += 1
                    continue
                
                existing_product = Product.query.filter_by(kode_produk=kode_produk).first()
                if existing_product:
                    existing_product.nama_produk = nama_produk
                    existing_product.saldo_awal = saldo_awal
                    update_count += 1
                else:
                    product = Product(
                        kode_produk=kode_produk,
                        nama_produk=nama_produk,
                        saldo_awal=saldo_awal
                    )
                    db.session.add(product)
                    success_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        if success_count > 0 or update_count > 0:
            db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Import completed. {success_count} products imported, {update_count} products updated, {error_count} errors",
            "success_count": success_count,
            "update_count": update_count,
            "error_count": error_count,
            "errors": errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@import_export_bp.route('/export/products', methods=['GET'])
def export_products():
    try:
        products = Product.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["kode_produk", "nama_produk", "saldo_awal", "created_at"])
        
        # Write data
        for product in products:
            writer.writerow([
                product.kode_produk,
                product.nama_produk,
                product.saldo_awal,
                product.created_at.strftime("%Y-%m-%d %H:%M:%S") if product.created_at else ""
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@import_export_bp.route('/sessions/<int:session_id>/export', methods=['GET'])
def export_session_csv(session_id):
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        details = StockOpnameDetail.query.filter_by(session_id=session_id).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "kode_produk", "nama_produk", "saldo_awal", 
            "jumlah_barang", "catatan", "created_at"
        ])
        
        # Write data
        for detail in details:
            writer.writerow([
                detail.product.kode_produk,
                detail.product.nama_produk,
                detail.product.saldo_awal,
                detail.jumlah_barang,
                detail.catatan or "",
                detail.created_at.strftime("%Y-%m-%d %H:%M:%S") if detail.created_at else ""
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=stock_opname_{session.lokasi}_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@import_export_bp.route('/export/stock-opname/<int:session_id>/excel', methods=['GET'])
def export_session_excel(session_id):
    try:
        session = StockOpnameSession.query.get_or_404(session_id)
        details = StockOpnameDetail.query.filter_by(session_id=session_id).all()
        
        # Prepare data for Excel
        data = []
        for detail in details:
            data.append({
                'Kode Produk': detail.product.kode_produk,
                "Nama Produk": detail.product.nama_produk,
                "Saldo Awal": detail.product.saldo_awal,
                "Jumlah Barang": detail.jumlah_barang,
                'Catatan': detail.catatan or '',
                'Waktu Input': detail.created_at.strftime('%Y-%m-%d %H:%M:%S') if detail.created_at else ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write main data
            df.to_excel(writer, sheet_name='Stock Opname', index=False)
            
            # Write summary sheet
            summary_data = {
                'Informasi': ['Lokasi', 'Waktu Mulai', 'Waktu Selesai', 'Status', 'Total Item'],
                'Detail': [
                    session.lokasi,
                    session.waktu_mulai.strftime('%Y-%m-%d %H:%M:%S') if session.waktu_mulai else '',
                    session.waktu_selesai.strftime('%Y-%m-%d %H:%M:%S') if session.waktu_selesai else 'Belum selesai',
                    session.status,
                    len(details)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=stock_opname_{session.lokasi}_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@import_export_bp.route("/template/products", methods=["GET"])
def download_template():
    try:
        # Define the headers for your Excel template
        headers = ["kode_produk", "nama_produk", "saldo_awal"]
        
        # Create an empty DataFrame with these headers
        df = pd.DataFrame(columns=headers)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Products Template", index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response.headers["Content-Disposition"] = "attachment; filename=template_products.xlsx"
        
        return response
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@import_export_bp.route("/export/products/excel", methods=["GET"])
def export_products_excel():
    try:
        products = Product.query.all()

        # Prepare data for Excel
        data = []
        for product in products:
            data.append({
                "Kode Produk": product.kode_produk,
                "Nama Produk": product.nama_produk,
                "Saldo Awal": product.saldo_awal,
                "Tanggal Dibuat": product.created_at.strftime("%Y-%m-%d %H:%M:%S") if product.created_at else ""
            })

        # Create DataFrame
        df = pd.DataFrame(data)

        # Create Excel file in memory
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Products", index=False)

        output.seek(0)

        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response.headers["Content-Disposition"] = f"attachment; filename=products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"

        return response

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@import_export_bp.route("/template/products/excel", methods=["GET"])
def download_excel_template():
    try:
        # Define the headers for your Excel template
        headers = ["Kode", "Nama Barang", "Jumlah"]
        
        # Create an empty DataFrame with these headers
        df = pd.DataFrame(columns=headers)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Products Template", index=False)
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response.headers["Content-Disposition"] = "attachment; filename=template_products.xlsx"
        
        return response
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
