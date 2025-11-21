# auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from db import get_db_connection
from psycopg2.extras import RealDictCursor

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")  # set in .env for production

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    role = data.get('role', 'technician')

    if not all([name, email, phone, password]):
        return jsonify({'error': 'All fields are required'}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check if email already exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'error': 'Email already registered'}), 400

    password_hash = generate_password_hash(password)
    cur.execute("""
        INSERT INTO users (name, email, phone, password_hash, role)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (name, email, phone, password_hash, role))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': user['id'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=6)
    }, SECRET_KEY, algorithm='HS256')

    # In PyJWT >=2.0 token is a str; ensure we return str
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'role': user['role']
    })

@auth_bp.route('/user-info', methods=['GET'])
def get_user_info():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Token missing'}), 401

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = decoded['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT name, role FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user)
