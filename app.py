import os
import io
import base64
from flask import Flask, render_template, request, send_file
from weasyprint import HTML

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    # 1. Ambil data teks dari Form Input
    client_name = request.form.get('client_name', 'PT Client Mandiri')
    service_id = request.form.get('service_id', 'CID-1001')
    service_type = request.form.get('service_type', 'Dedicated Internet')
    bandwidth = request.form.get('bandwidth', '100 Mbps')
    period = request.form.get('period', 'Juli 2026')
    target_sla = float(request.form.get('target_sla', 99.5))
    
    # 2. Ambil data Outage Log
    dates = request.form.getlist('outage_date[]')
    durations = request.form.getlist('outage_duration[]')
    categories = request.form.getlist('outage_category[]')
    descriptions = request.form.getlist('outage_desc[]')
    
    outage_logs = []
    total_unplanned_downtime = 0
    
    for i in range(len(dates)):
        if dates[i].strip():
            dur = int(durations[i]) if durations[i].isdigit() else 0
            cat = categories[i]
            outage_logs.append({
                'no': i + 1,
                'date': dates[i],
                'duration': dur,
                'category': cat,
                'desc': descriptions[i]
            })
            if cat == 'Unplanned':
                total_unplanned_downtime += dur

    # 3. Perhitungan SLA (30 Hari = 43200 Menit)
    total_minutes_month = 43200
    actual_sla = ((total_minutes_month - total_unplanned_downtime) / total_minutes_month) * 100
    actual_sla = round(actual_sla, 2)
    
    hours = total_unplanned_downtime // 60
    mins = total_unplanned_downtime % 60
    downtime_str = f"{hours} Jam {mins} Menit" if hours > 0 else f"{mins} Menit"

    status = "PASSED / COMPLIANT" if actual_sla >= target_sla else "NON-COMPLIANT"
    
    # 4. Handle Upload Gambar Grafik (Convert ke Base64)
    graph_file = request.files.get('graph_image')
    graph_base64 = None
    
    if graph_file and graph_file.filename != '':
        graph_bytes = graph_file.read()
        graph_base64 = base64.b64encode(graph_bytes).decode('utf-8')

    # 5. Data Context untuk Template HTML
    data = {
        'company_name': 'PT RAJEG MEDIA TELEKOMUNIKASI',
        'client_name': client_name,
        'service_id': service_id,
        'service_type': service_type,
        'bandwidth': bandwidth,
        'period': period,
        'target_sla': target_sla,
        'actual_sla': actual_sla,
        'downtime_str': downtime_str,
        'total_unplanned_downtime': total_unplanned_downtime,
        'status': status,
        'outage_logs': outage_logs,
        'graph_base64': graph_base64,
        'doc_id': f"SLA-{period.replace(' ', '')}-{service_id}"
    }

    # 6. Render HTML & Generate PDF
    rendered_html = render_template('report_template.html', **data)
    
    pdf_io = io.BytesIO()
    HTML(string=rendered_html).write_pdf(pdf_io)
    pdf_io.seek(0)

    filename = f"Laporan_SLA_{client_name.replace(' ', '_')}_{period.replace(' ', '_')}.pdf"
    return send_file(pdf_io, download_name=filename, as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    print("Aplikasi SLA Generator Berjalan di http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)