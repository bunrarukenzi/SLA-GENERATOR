import os
import io
import base64
import calendar
from datetime import datetime
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    # 1. Ambil data teks dari Form Input
    company_name = request.form.get('company_name', 'PT RAJEG MEDIA TELEKOMUNIKASI').strip()
    client_name = request.form.get('client_name', 'PT Client Mandiri').strip()
    service_id = request.form.get('service_id', 'CID-1001').strip()
    service_type = request.form.get('service_type', 'Dedicated Internet').strip()
    bandwidth = request.form.get('bandwidth', '100 Mbps').strip()
    period = request.form.get('period', 'Juli 2026').strip()
    
    try:
        target_sla = float(request.form.get('target_sla', 99.5))
    except (ValueError, TypeError):
        target_sla = 99.5

    # 2. Hitung total menit dalam bulan (dinamis berdasarkan period)
    total_minutes_month = get_month_minutes(period)
    
    # 3. Ambil data Outage Log
    dates = request.form.getlist('outage_date[]')
    durations = request.form.getlist('outage_duration[]')
    categories = request.form.getlist('outage_category[]')
    descriptions = request.form.getlist('outage_desc[]')
    
    outage_logs = []
    total_unplanned_downtime = 0
    total_planned_downtime = 0
    
    for i in range(len(dates)):
        if dates[i].strip():
            try:
                dur = int(durations[i]) if durations[i].strip().isdigit() else 0
            except (ValueError, IndexError):
                dur = 0
            
            cat = categories[i] if i < len(categories) else 'Unplanned'
            desc = descriptions[i] if i < len(descriptions) else ''
            
            outage_logs.append({
                'no': len(outage_logs) + 1,
                'date': dates[i].strip(),
                'duration': dur,
                'category': cat,
                'desc': desc.strip()
            })
            
            if cat == 'Unplanned':
                total_unplanned_downtime += dur
            else:
                total_planned_downtime += dur

    # 4. Perhitungan SLA
    if total_minutes_month > 0:
        actual_sla = ((total_minutes_month - total_unplanned_downtime) / total_minutes_month) * 100
    else:
        actual_sla = 100.0
    actual_sla = round(actual_sla, 4)
    
    # Format downtime string
    hours = total_unplanned_downtime // 60
    mins = total_unplanned_downtime % 60
    if hours > 0 and mins > 0:
        downtime_str = f"{hours} Jam {mins} Menit"
    elif hours > 0:
        downtime_str = f"{hours} Jam"
    elif mins > 0:
        downtime_str = f"{mins} Menit"
    else:
        downtime_str = "0 Menit (Tidak Ada Downtime)"

    # Status SLA
    status = "COMPLIANT" if actual_sla >= target_sla else "NON-COMPLIANT"
    sla_passed = actual_sla >= target_sla
    
    # 5. Handle Upload Gambar Grafik (Convert ke Base64)
    graph_file = request.files.get('graph_image')
    graph_base64 = None
    
    if graph_file and graph_file.filename != '':
        graph_bytes = graph_file.read()
        graph_base64 = base64.b64encode(graph_bytes).decode('utf-8')
        # Deteksi MIME type
        filename_lower = graph_file.filename.lower()
        if filename_lower.endswith('.png'):
            graph_mime = 'image/png'
        elif filename_lower.endswith('.webp'):
            graph_mime = 'image/webp'
        else:
            graph_mime = 'image/jpeg'
    else:
        graph_mime = 'image/png'

    # 6. Data Context untuk Template HTML
    days_in_month = total_minutes_month // 1440
    data = {
        'company_name': company_name,
        'client_name': client_name,
        'service_id': service_id,
        'service_type': service_type,
        'bandwidth': bandwidth,
        'period': period,
        'target_sla': target_sla,
        'actual_sla': actual_sla,
        'downtime_str': downtime_str,
        'total_unplanned_downtime': total_unplanned_downtime,
        'total_planned_downtime': total_planned_downtime,
        'total_minutes_month': total_minutes_month,
        'days_in_month': days_in_month,
        'status': status,
        'sla_passed': sla_passed,
        'outage_logs': outage_logs,
        'graph_base64': graph_base64,
        'graph_mime': graph_mime,
        'doc_id': f"SLA-{period.replace(' ', '')}-{service_id}",
        'generated_at': datetime.now().strftime('%d %B %Y, %H:%M WIB')
    }

    # 7. Render HTML & Generate PDF
    rendered_html = render_template('report_template.html', **data)
    
    pdf_io = io.BytesIO()
    HTML(string=rendered_html).write_pdf(pdf_io)
    pdf_io.seek(0)

    filename = f"Laporan_SLA_{client_name.replace(' ', '_')}_{period.replace(' ', '_')}.pdf"
    return send_file(pdf_io, download_name=filename, as_attachment=True, mimetype='application/pdf')


def get_month_minutes(period_str):
    """Hitung total menit dalam bulan berdasarkan string periode (mis: 'Juli 2026')"""
    month_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
        'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    
    try:
        parts = period_str.strip().split()
        if len(parts) >= 2:
            month_name = parts[0].lower()
            year = int(parts[1])
            month_num = month_map.get(month_name)
            if month_num:
                days = calendar.monthrange(year, month_num)[1]
                return days * 24 * 60
    except (ValueError, IndexError):
        pass
    
    # Default: 30 hari
    return 43200


# Import WeasyPrint (di bawah supaya error message lebih jelas)
try:
    from weasyprint import HTML
except ImportError:
    print("ERROR: WeasyPrint belum terinstall!")
    print("Jalankan: pip install weasyprint")
    exit(1)


if __name__ == '__main__':
    print("=" * 50)
    print("  SLA Generator - NOC Report Tool")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host='127.0.0.1', port=5000, debug=True)