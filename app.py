from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4, portrait
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io

app = Flask(__name__, static_folder='.')
CORS(app)

# =====================================================
# MONGODB ATLAS CONNECTION
# =====================================================


MONGO_URI = f"mongodb+srv://milk:milk@cluster0.yjjzkrq.mongodb.net/?appName=Cluster0"

DB_NAME = 'heritage_daily_db'
COLLECTION_NAME = 'products'
SOLD_COLLECTION_NAME = 'sold_products'

products_collection = None
sold_collection = None

def format_indian_rupee(amount):
    """Format amount as Indian Rupee"""
    return f"₹{amount:,.2f}"

def connect_to_mongodb():
    global products_collection, sold_collection
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[DB_NAME]
        products_collection = db[COLLECTION_NAME]
        sold_collection = db[SOLD_COLLECTION_NAME]
        
        # Create indexes
        products_collection.create_index([("inDateTime", 1)])
        products_collection.create_index([("productName", 1)])
        sold_collection.create_index([("soldDateTime", 1)])
        sold_collection.create_index([("productName", 1)])
        
        print("\n" + "="*60)
        print("✅ CONNECTED TO MONGODB ATLAS SUCCESSFULLY!")
        print("="*60)
        print(f"📊 Products Collection: {COLLECTION_NAME}")
        print(f"📊 Sold Products Collection: {SOLD_COLLECTION_NAME}")
        print("="*60)
        return True
    except Exception as e:
        print("\n" + "="*60)
        print("❌ MONGODB ATLAS CONNECTION FAILED!")
        print(f"Error: {e}")
        print("="*60 + "\n")
        return False

def serialize_product(product):
    if product is None:
        return None
    return {
        'id': str(product['_id']),
        '_id': str(product['_id']),
        'productName': product.get('productName', ''),
        'count': product.get('count', 1),
        'militaryLiter': product.get('militaryLiter', 0),
        'price': product.get('price', 0),
        'inDateTime': product.get('inDateTime', '')
    }

def serialize_sold_product(sold):
    if sold is None:
        return None
    return {
        'id': str(sold['_id']),
        '_id': str(sold['_id']),
        'productName': sold.get('productName', ''),
        'soldCount': sold.get('soldCount', 1),
        'militaryLiter': sold.get('militaryLiter', 0),
        'price': sold.get('price', 0),
        'totalAmount': sold.get('totalAmount', 0),
        'soldDateTime': sold.get('soldDateTime', ''),
        'originalProductId': sold.get('originalProductId', '')
    }

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# =====================================================
# PRODUCTS API
# =====================================================

@app.route('/api/products', methods=['GET'])
def get_products():
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        products = list(products_collection.find().sort('inDateTime', 1))
        return jsonify([serialize_product(p) for p in products])
    except Exception as e:
        return jsonify({'error': f'Failed to fetch products: {str(e)}'}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        data = request.get_json()
        product = {
            'productName': data['productName'].strip(),
            'count': int(data['count']),
            'militaryLiter': float(data['militaryLiter']),
            'price': float(data['price']),
            'inDateTime': data['inDateTime'],
            'createdAt': datetime.now().isoformat()
        }
        result = products_collection.insert_one(product)
        product['_id'] = result.inserted_id
        return jsonify(serialize_product(product)), 201
    except Exception as e:
        return jsonify({'error': f'Failed to save: {str(e)}'}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        data = request.get_json()
        update_fields = {}
        if 'productName' in data:
            update_fields['productName'] = data['productName'].strip()
        if 'count' in data:
            update_fields['count'] = int(data['count'])
        if 'militaryLiter' in data:
            update_fields['militaryLiter'] = float(data['militaryLiter'])
        if 'price' in data:
            update_fields['price'] = float(data['price'])
        update_fields['updatedAt'] = datetime.now().isoformat()
        
        result = products_collection.update_one({'_id': ObjectId(product_id)}, {'$set': update_fields})
        if result.matched_count == 0:
            return jsonify({'error': 'Product not found'}), 404
        updated_product = products_collection.find_one({'_id': ObjectId(product_id)})
        return jsonify(serialize_product(updated_product)), 200
    except Exception as e:
        return jsonify({'error': f'Failed to update: {str(e)}'}), 500

@app.route('/api/products/<product_id>', methods=['PATCH'])
def patch_product(product_id):
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        data = request.get_json()
        if 'count' in data:
            new_count = int(data['count'])
            if new_count < 1:
                return jsonify({'error': 'Count must be at least 1'}), 400
            result = products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {'count': new_count, 'updatedAt': datetime.now().isoformat()}}
            )
            if result.matched_count == 0:
                return jsonify({'error': 'Product not found'}), 404
            updated_product = products_collection.find_one({'_id': ObjectId(product_id)})
            return jsonify(serialize_product(updated_product)), 200
        return jsonify({'error': 'No fields to update'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to patch: {str(e)}'}), 500

@app.route('/api/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        result = products_collection.delete_one({'_id': ObjectId(product_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete: {str(e)}'}), 500

# =====================================================
# SELL PRODUCT API
# =====================================================

@app.route('/api/sell', methods=['POST'])
def sell_product():
    if products_collection is None or sold_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        data = request.get_json()
        product_id = data.get('productId')
        sell_count = int(data.get('sellCount', 1))
        
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        current_count = product.get('count', 1)
        if sell_count > current_count:
            return jsonify({'error': f'Only {current_count} items available'}), 400
        
        price = product.get('price', 0)
        total_amount = price * sell_count
        
        sold_record = {
            'productName': product.get('productName'),
            'soldCount': sell_count,
            'militaryLiter': product.get('militaryLiter'),
            'price': price,
            'totalAmount': total_amount,
            'soldDateTime': datetime.now().isoformat(),
            'originalProductId': product_id,
            'originalCountBefore': current_count
        }
        
        sold_result = sold_collection.insert_one(sold_record)
        
        new_count = current_count - sell_count
        if new_count == 0:
            products_collection.delete_one({'_id': ObjectId(product_id)})
            product_deleted = True
        else:
            products_collection.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': {'count': new_count, 'updatedAt': datetime.now().isoformat()}}
            )
            product_deleted = False
        
        sold_record['_id'] = sold_result.inserted_id
        
        return jsonify({
            'message': f'Successfully sold {sell_count} item(s)',
            'soldRecord': serialize_sold_product(sold_record),
            'remainingCount': new_count if not product_deleted else 0,
            'productDeleted': product_deleted
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to sell product: {str(e)}'}), 500

# =====================================================
# SOLD PRODUCTS API
# =====================================================

@app.route('/api/sold', methods=['GET'])
def get_sold_products():
    if sold_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        sold_products = list(sold_collection.find().sort('soldDateTime', -1))
        return jsonify([serialize_sold_product(p) for p in sold_products])
    except Exception as e:
        return jsonify({'error': f'Failed to fetch sold products: {str(e)}'}), 500

@app.route('/api/sold/<sold_id>', methods=['DELETE'])
def delete_sold_product(sold_id):
    if sold_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        result = sold_collection.delete_one({'_id': ObjectId(sold_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Sold product not found'}), 404
        return jsonify({'message': 'Sold product deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete: {str(e)}'}), 500

# =====================================================
# PDF EXPORTS
# =====================================================

@app.route('/api/export/pdf', methods=['GET'])
def export_pdf():
    if products_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        products = list(products_collection.find().sort('inDateTime', 1))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                                rightMargin=30, leftMargin=30, 
                                topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                     fontSize=20, textColor=colors.HexColor('#5a3e1b'),
                                     alignment=1, spaceAfter=20)
        
        story = []
        title = Paragraph("🏺 Heritage Daily Input App - Available Products Report", title_style)
        story.append(title)
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST", styles['Normal']))
        story.append(Spacer(1, 20))
        
        total_products = len(products)
        total_quantity = sum(p.get('count', 1) for p in products)
        grand_total = sum((p.get('price', 0) * p.get('count', 1)) for p in products)
        
        summary_data = [
            ['Total Products', 'Total Quantity', 'Inventory Value (₹)'],
            [str(total_products), str(total_quantity), format_indian_rupee(grand_total)]
        ]
        summary_table = Table(summary_data, colWidths=[150, 150, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5a2b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d4c4a8')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        table_data = [['#', 'Product Name', 'Count', 'Mil. Liter', 'Price (₹)', 'Total Cost (₹)', 'In Date & Time']]
        for idx, p in enumerate(products, 1):
            price = p.get('price', 0)
            count = p.get('count', 1)
            total_cost = price * count
            in_date = datetime.fromisoformat(p['inDateTime']).strftime('%Y-%m-%d %H:%M') if p.get('inDateTime') else 'N/A'
            table_data.append([
                str(idx), p.get('productName', 'N/A'), str(count),
                f"{p.get('militaryLiter', 0):.2f}", format_indian_rupee(price),
                format_indian_rupee(total_cost), in_date
            ])
        
        col_widths = [40, 140, 50, 70, 80, 90, 130]
        product_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5a3e1b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d4c4a8')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fcf6ed')]),
        ]))
        story.append(product_table)
        
        doc.build(story)
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=available_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
        )
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

@app.route('/api/export/sold/pdf', methods=['GET'])
def export_sold_pdf():
    """Generate PDF for sold products"""
    if sold_collection is None:
        return jsonify({'error': 'MongoDB not connected'}), 500
    try:
        sold_products = list(sold_collection.find().sort('soldDateTime', -1))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                                rightMargin=30, leftMargin=30, 
                                topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                     fontSize=20, textColor=colors.HexColor('#8b5a2b'),
                                     alignment=1, spaceAfter=20)
        
        story = []
        title = Paragraph("🛒 Heritage Daily Input App - Sold Products Report", title_style)
        story.append(title)
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Calculate statistics
        total_sold_items = len(sold_products)
        total_quantity = sum(s.get('soldCount', 1) for s in sold_products)
        total_sales = sum(s.get('totalAmount', 0) for s in sold_products)
        
        summary_data = [
            ['Total Sold Transactions', 'Total Quantity Sold', 'Total Sales (₹)'],
            [str(total_sold_items), str(total_quantity), format_indian_rupee(total_sales)]
        ]
        summary_table = Table(summary_data, colWidths=[180, 150, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5a2b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d4c4a8')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Sold products table
        table_data = [['#', 'Product Name', 'Sold Count', 'Mil. Liter', 'Price (₹)', 'Total Amount (₹)', 'Sold Date & Time']]
        for idx, s in enumerate(sold_products, 1):
            sold_date = datetime.fromisoformat(s['soldDateTime']).strftime('%Y-%m-%d %H:%M:%S') if s.get('soldDateTime') else 'N/A'
            table_data.append([
                str(idx),
                s.get('productName', 'N/A'),
                str(s.get('soldCount', 1)),
                f"{s.get('militaryLiter', 0):.2f}",
                format_indian_rupee(s.get('price', 0)),
                format_indian_rupee(s.get('totalAmount', 0)),
                sold_date
            ])
        
        col_widths = [40, 140, 60, 70, 80, 90, 140]
        sold_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        sold_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5a3e1b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d4c4a8')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fcf6ed')]),
        ]))
        story.append(sold_table)
        
        # Footer
        story.append(Spacer(1, 20))
        footer_note = Paragraph("All amounts are in Indian Rupee (₹) | Generated by Heritage Daily Input App", 
                                styles['Normal'])
        story.append(footer_note)
        
        doc.build(story)
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=sold_products_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
        )
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    if products_collection is None:
        return jsonify({'status': 'error', 'mongodb': 'disconnected'}), 500
    try:
        count = products_collection.count_documents({})
        sold_count = sold_collection.count_documents({}) if sold_collection else 0
        return jsonify({
            'status': 'healthy', 
            'mongodb': 'connected', 
            'productCount': count,
            'soldCount': sold_count
        }), 200
    except:
        return jsonify({'status': 'degraded'}), 500

if __name__ == '__main__':
    connect_to_mongodb()
    app.run(debug=True, port=5000)
