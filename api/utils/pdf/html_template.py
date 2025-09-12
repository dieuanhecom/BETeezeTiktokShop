def create_pdf_template(order_data):
    """
    Create HTML template for PDF generation
    
    Args:
        order_data (dict): Order data containing:
            - lo: Batch number
            - ngay: Date
            - stt: Sequential number
            - soLuongAo: Quantity of shirts
            - maTracking: Tracking code
            - loaiAo: Shirt type
            - mau: Color
            - size: Size
            - anh: Image URL
    
    Returns:
        str: HTML template string
    """
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0 20px; 
                font-size: 12px;
                line-height: 1.4;
            }}
            .table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin-bottom: 30px; 
            }}
            .table td, .table th {{ 
                border: 1px solid #000; 
                padding: 8px; 
                font-size: 11px;
                text-align: left;
            }}
            .table th {{ 
                background-color: #f2f2f2; 
                font-weight: bold;
            }}
            .images-container {{ 
                display: flex; 
                justify-content: space-between; 
                margin-top: 20px;
                gap: 10px;
            }}
            .product-image {{ 
                width: 45%; 
                height: 250px; 
                object-fit: cover; 
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
            .logo {{ 
                font-size: 20px; 
                font-weight: bold; 
                position: absolute;
            }}
            .logo.gozen {{ 
                top: 20px; 
                left: 20px; 
            }}
            .logo.suzuka {{ 
                bottom: 20px; 
                right: 20px; 
            }}
            .page-break {{
                page-break-after: always;
            }}
            .color-bold {{
                font-weight: bold;
            }}
            .container {{
                position: relative;
                min-height: 400px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <table class="table">
                <tr>
                    <td><strong>Lô</strong></td>
                    <td>{order_data.get('lo', '')}</td>
                </tr>
                <tr>
                    <td><strong>Ngày</strong></td>
                    <td>{order_data.get('ngay', '')}</td>
                </tr>
                <tr>
                    <td><strong>STT</strong></td>
                    <td>{order_data.get('stt', '')}</td>
                </tr>
                <tr>
                    <td><strong>Số Lượng Áo</strong></td>
                    <td>{order_data.get('soLuongAo', '')}</td>
                </tr>
                <tr>
                    <td><strong>Mã tracking</strong></td>
                    <td>{order_data.get('maTracking', '')}</td>
                </tr>
                <tr>
                    <td><strong>Loại Áo</strong></td>
                    <td>{order_data.get('loaiAo', '')}</td>
                </tr>
                <tr>
                    <td><strong>Màu</strong></td>
                    <td class="color-bold">{order_data.get('mau', '')}</td>
                </tr>
                <tr>
                    <td><strong>Size</strong></td>
                    <td>{order_data.get('size', '')}</td>
                </tr>
            </table>
            
            <div class="images-container">
                <img src="{order_data.get('anh', '')}" class="product-image" alt="Product" />
            </div>
        </div>
        
        <div class="page-break"></div>
    </body>
    </html>
    """
    
    return html_template 