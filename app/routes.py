from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Room, Reservation, db
from datetime import datetime

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return redirect(url_for("auth.login"))

@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard: show current user's reservations and a link to the reserve form."""
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', reservations=reservations)

@main_bp.route("/reserve", methods=["GET", "POST"])
@login_required
def reserve():
    types = ["Single", "Double", "Suite"]

    # Support search parameters in querystring (so the search UI can live here)
    q_type = request.args.get('type') or request.form.get('type')
    q_checkin = request.args.get('checkin') or request.form.get('checkin')
    q_checkout = request.args.get('checkout') or request.form.get('checkout')

    rooms_query = Room.query.filter_by(available=True)
    if q_type:
        rooms_query = rooms_query.filter_by(type=q_type)
    rooms = rooms_query.all()

    # If dates provided, filter out rooms with overlapping reservations
    try:
        if q_checkin and q_checkout:
            checkin_dt = datetime.fromisoformat(q_checkin).date()
            checkout_dt = datetime.fromisoformat(q_checkout).date()
            if checkin_dt >= checkout_dt:
                flash('La fecha de check-out debe ser posterior a la de check-in', 'danger')
                return render_template('reserve.html', types=types, rooms=[], type=q_type, checkin=q_checkin, checkout=q_checkout)

            available_rooms = []
            for r in rooms:
                overlapping = Reservation.query.filter(
                    Reservation.room_id == r.id,
                    Reservation.checkout > checkin_dt,
                    Reservation.checkin < checkout_dt
                ).first()
                if not overlapping:
                    available_rooms.append(r)
            rooms = available_rooms
    except ValueError:
        flash('Formato de fecha inválido. Use YYYY-MM-DD', 'danger')

    # Handle reservation submission
    if request.method == "POST":
        room_id = request.form.get("room_id")
        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")

        if not room_id or not checkin or not checkout:
            flash('Todos los campos son requeridos para reservar', 'danger')
            return redirect(url_for('main.reserve'))

        try:
            checkin_dt = datetime.fromisoformat(checkin).date()
            checkout_dt = datetime.fromisoformat(checkout).date()
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD', 'danger')
            return redirect(url_for('main.reserve'))

        if checkin_dt >= checkout_dt:
            flash('La fecha de check-out debe ser posterior a la de check-in', 'danger')
            return redirect(url_for('main.reserve'))

        # ensure room exists and is available for the requested dates
        room = Room.query.get(int(room_id))
        if not room or not room.available:
            flash('La habitación no está disponible', 'danger')
            return redirect(url_for('main.reserve'))

        overlapping = Reservation.query.filter(
            Reservation.room_id == room.id,
            Reservation.checkout > checkin_dt,
            Reservation.checkin < checkout_dt
        ).first()
        if overlapping:
            flash('La habitación no está disponible en esas fechas', 'danger')
            return redirect(url_for('main.reserve'))

        reservation = Reservation(
            user_id=current_user.id,
            room_id=room.id,
            checkin=checkin_dt,
            checkout=checkout_dt
        )
        db.session.add(reservation)
        # marcar habitación como no disponible
        room.available = False
        db.session.commit()

        flash("Reserva realizada con éxito.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template('reserve.html', types=types, rooms=rooms, type=q_type, checkin=q_checkin, checkout=q_checkout)


@main_bp.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    """Create a new Room. Expects form fields: number, type. Returns JSON."""
    number = request.form.get('number')
    rtype = request.form.get('type')
    if not number or not rtype:
        return jsonify({'success': False, 'error': 'number and type required'}), 400

    # check uniqueness
    existing = Room.query.filter_by(number=number).first()
    if existing:
        return jsonify({'success': False, 'error': 'room already exists'}), 409

    room = Room(number=number, type=rtype, available=True)
    db.session.add(room)
    db.session.commit()

    return jsonify({'success': True, 'room': {'id': room.id, 'number': room.number, 'type': room.type}})
