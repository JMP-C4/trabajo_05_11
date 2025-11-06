import pytest
from app import create_app
from app.models import init_db
import tempfile
import os
from datetime import datetime, timedelta

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path
    })
    
    # Initialize the test database
    with app.app_context():
        init_db(db_path)
    
    yield app
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Client with logged in user"""
    with client.session_transaction() as session:
        session['user_id'] = 1  # Use admin user created by init_db
    return client

def test_reserve_page_not_found(client):
    """Test accessing non-existent room"""
    response = client.get('/reserve/999')
    assert response.status_code == 404

def test_reserve_page_loads(client):
    """Test reserve page loads for existing room"""
    response = client.get('/reserve/1')  # Room S-1
    assert response.status_code == 200
    assert b'Confirmar Reserva' in response.data
    assert b'S-1' in response.data

def test_reserve_requires_login(client):
    """Test that reservation requires login"""
    response = client.post('/reserve/1', data={
        'checkin': '2025-12-01',
        'checkout': '2025-12-05'
    })
    assert b'iniciar sesi' in response.data  # 'iniciar sesión'

def test_successful_reservation(auth_client, app):
    """Test making a successful reservation"""
    response = auth_client.post('/reserve/1', data={
        'checkin': '2025-12-01',
        'checkout': '2025-12-05',
        'card_number': '1234567890123456',
        'expiry': '12/25',
        'cvv': '123'
    }, follow_redirects=True)
    assert b'Reserva creada correctamente' in response.data
    
    # Verify reservation in database
    with app.app_context():
        db = app.config['DATABASE']
        from app.models import get_conn
        conn = get_conn(db)
        cur = conn.cursor()
        reservation = cur.execute(
            'SELECT * FROM reservations WHERE room_id = 1'
        ).fetchone()
        assert reservation is not None
        assert reservation['status'] == 'CONFIRMADA'
        conn.close()

def test_overlapping_reservation(auth_client, app):
    """Test attempting to reserve an already booked room"""
    # First create a reservation
    with app.app_context():
        db = app.config['DATABASE']
        from app.models import get_conn
        conn = get_conn(db)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO reservations (user_id, room_id, checkin, checkout, total, status, created_at)
            VALUES (1, 1, '2025-12-01', '2025-12-05', 200, 'CONFIRMADA', datetime('now'))
        ''')
        conn.commit()
        conn.close()
    
    # Try to make overlapping reservation
    response = auth_client.post('/reserve/1', data={
        'checkin': '2025-12-03',
        'checkout': '2025-12-07'
    }, follow_redirects=True)
    assert b'no est' in response.data  # 'no está disponible'

def test_reservation_total_calculation(auth_client, app):
    """Test that reservation total is calculated correctly"""
    # Get room price first
    with app.app_context():
        db = app.config['DATABASE']
        from app.models import get_conn
        conn = get_conn(db)
        cur = conn.cursor()
        room = cur.execute('''
            SELECT r.*, t.price 
            FROM rooms r 
            JOIN room_types t ON r.type_id = t.id 
            WHERE r.id = 1
        ''').fetchone()
        price_per_night = room['price']
        conn.close()
    
    # Make a 4-night reservation
    response = auth_client.post('/reserve/1', data={
        'checkin': '2025-12-01',
        'checkout': '2025-12-05',
        'card_number': '1234567890123456',
        'expiry': '12/25',
        'cvv': '123'
    }, follow_redirects=True)
    
    # Verify total in database
    with app.app_context():
        conn = get_conn(db)
        cur = conn.cursor()
        reservation = cur.execute(
            'SELECT * FROM reservations WHERE room_id = 1'
        ).fetchone()
        assert reservation['total'] == price_per_night * 4  # 4 nights
        conn.close()
