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

def test_search_page(client):
    """Test that search page loads with room types"""
    response = client.get('/search')
    assert response.status_code == 200
    assert b'Buscar habitaciones' in response.data
    assert b'Simple' in response.data
    assert b'Doble' in response.data
    assert b'Suite' in response.data

def test_search_invalid_dates(client):
    """Test search with invalid date format"""
    response = client.post('/search', data={
        'tipo': 'Simple',
        'checkin': 'invalid-date',
        'checkout': '2025-11-10'
    })
    assert b'Formato de fecha inv' in response.data  # 'Formato de fecha inválido'

def test_search_checkout_before_checkin(client):
    """Test search with checkout date before checkin"""
    response = client.post('/search', data={
        'tipo': 'Simple',
        'checkin': '2025-11-10',
        'checkout': '2025-11-09'
    })
    assert b'check-out debe ser posterior' in response.data

def test_search_available_rooms(client):
    """Test searching for available rooms"""
    # Search for rooms with valid dates
    response = client.post('/search', data={
        'tipo': 'Simple',
        'checkin': '2025-12-01',
        'checkout': '2025-12-05'
    })
    assert response.status_code == 200
    assert b'S-1' in response.data  # Should find at least one Simple room
    assert b'Reservar' in response.data

def test_search_with_existing_reservation(client, app):
    """Test search with an existing reservation"""
    # First create a reservation
    with app.app_context():
        db = app.config['DATABASE']
        from app.models import get_conn
        conn = get_conn(db)
        cur = conn.cursor()
        
        # Add a test reservation for room S-1
        cur.execute('''
            INSERT INTO reservations (user_id, room_id, checkin, checkout, total, status, created_at)
            SELECT 1, r.id, ?, ?, 200, 'CONFIRMADA', datetime('now')
            FROM rooms r
            WHERE r.number = 'S-1'
        ''', ('2025-12-01', '2025-12-03'))
        conn.commit()
        conn.close()

    # Now search for rooms during the same period
    response = client.post('/search', data={
        'tipo': 'Simple',
        'checkin': '2025-12-01',
        'checkout': '2025-12-03'
    })
    assert response.status_code == 200
    assert b'S-1' not in response.data  # Room S-1 should not be available
