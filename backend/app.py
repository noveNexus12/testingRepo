# app.py
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from auth import auth_bp
from db import get_db_connection
from iot_routes import iot_bp
import datetime
import io
import csv
import os
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080"
]}}, supports_credentials=True)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(iot_bp)

@app.route('/api/poles', methods=['GET'])
def get_poles():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT 
            pole_id, cluster_id, latitude, longitude,
            status, communication_status, state, district,
            city_or_village, mode, firmware_version, update_time
        FROM poles
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()

    now = datetime.datetime.utcnow()
    for row in data:
        if row.get('update_time'):
            row['update_time'] = row['update_time'].isoformat()

        display_status = row.get('communication_status', 'OFFLINE')

        if row['communication_status'] == 'OFFLINE' and row.get('update_time'):
            update_time = datetime.datetime.fromisoformat(row['update_time'])
            diff_days = (now - update_time).days
            display_status = 'MAINTENANCE' if diff_days < 3 else 'OFFLINE'
        elif row['communication_status'] == 'ONLINE':
            display_status = 'ONLINE'

        row['display_status'] = display_status

    return jsonify(data)


@app.route('/api/poles/<pole_id>', methods=['GET'])
def get_pole_details(pole_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            pole_id, cluster_id, latitude, longitude,
            status AS device_status, communication_status,
            state, district, city_or_village, mode,
            firmware_version, update_time
        FROM poles
        WHERE pole_id = %s
    """, (pole_id,))
    data = cur.fetchone()
    cur.close()
    conn.close()

    if not data:
        return jsonify({"error": "Pole not found"}), 404

    if data['update_time']:
        data['update_time'] = data['update_time'].isoformat()

    now = datetime.datetime.utcnow()
    display_status = data['communication_status']

    if data['communication_status'] == 'OFFLINE' and data['update_time']:
        update_time = datetime.datetime.fromisoformat(data['update_time'])
        diff_days = (now - update_time).days
        display_status = 'MAINTENANCE' if diff_days < 3 else 'OFFLINE'
    elif data['communication_status'] == 'ONLINE':
        display_status = 'ONLINE'

    data['display_status'] = display_status
    return jsonify(data)


@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    pole_id = request.args.get('pole_id')
    mode = request.args.get('mode', 'filtered')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if pole_id:
        if mode == 'filtered':
            cur.execute("""
                SELECT pole_id, status, signal_strength, timestamp
                FROM telemetry_data
                WHERE pole_id = %s
                  AND (timestamp::time BETWEEN '06:30' AND '07:00'
                       OR timestamp::time BETWEEN '18:00' AND '18:30')
                ORDER BY timestamp DESC
            """, (pole_id,))
        else:
            cur.execute("""
                SELECT pole_id, status, signal_strength, timestamp
                FROM telemetry_data
                WHERE pole_id = %s
                ORDER BY timestamp DESC
                LIMIT 24
            """, (pole_id,))
    else:
        cur.execute("""
            SELECT pole_id, status, signal_strength, timestamp
            FROM telemetry_data
            WHERE (timestamp::time BETWEEN '06:30' AND '07:00')
               OR (timestamp::time BETWEEN '18:00' AND '18:30')
            ORDER BY timestamp DESC
        """)

    data = cur.fetchall()
    cur.close()
    conn.close()

    for row in data:
        if row.get('timestamp'):
            row['timestamp'] = row['timestamp'].isoformat()

    return jsonify(data)


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT pole_id, message, severity, alert_status,
               alert_type, technician_id, action_taken,
               remarks, timestamp
        FROM alerts
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    data = cur.fetchall()
    cur.close()
    conn.close()

    for row in data:
        if row.get('timestamp'):
            row['timestamp'] = row['timestamp'].isoformat()

    return jsonify(data)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT COUNT(*)::int AS total FROM poles")
    total = cur.fetchone().get('total', 0)

    cur.execute("SELECT COUNT(*)::int AS active FROM poles WHERE status='ON'")
    active = cur.fetchone().get('active', 0)

    cur.execute("SELECT COUNT(*)::int AS inactive FROM poles WHERE status='OFF'")
    inactive = cur.fetchone().get('inactive', 0)

    cur.execute("SELECT COUNT(*)::int AS alerts FROM alerts WHERE alert_status='ACTIVE'")
    alerts = cur.fetchone().get('alerts', 0)

    cur.close()
    conn.close()
    return jsonify({
        "total": total,
        "active": active,
        "inactive": inactive,
        "alerts": alerts
    })


@app.route('/api/export/<table_name>', methods=['GET'])
def export_csv(table_name):
    valid_tables = {
        'telemetry': 'telemetry_data',
        'alerts': 'alerts',
        'poles': 'poles'
    }

    if table_name not in valid_tables:
        return jsonify({'error': 'Invalid dataset'}), 400

    start_date = request.args.get('start')
    end_date = request.args.get('end')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = f"SELECT * FROM {valid_tables[table_name]}"
    params = []

    if start_date and end_date:
        query += " WHERE timestamp BETWEEN %s AND %s"
        params = [start_date, end_date]

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("No data available")

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}_export.csv'
    return response

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "success", "message": "Connected to Supabase!", "time": str(result[0])}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
