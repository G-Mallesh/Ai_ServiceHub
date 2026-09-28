import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from backend.config import Config
from backend.database import query


# ============================================================
# APPLICATION
# ============================================================

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

app.config["SECRET_KEY"] = Config.SECRET_KEY


# ============================================================
# CONTEXT
# ============================================================

@app.context_processor
def inject_config():

    return {
        "google_maps_api_key": getattr(
            Config,
            "GOOGLE_MAPS_API_KEY",
            ""
        ),

        "razorpay_key_id": getattr(
            Config,
            "RAZORPAY_KEY_ID",
            ""
        )
    }


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if not session.get("user_id"):

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(*roles):

    def decorator(function):

        @wraps(function)
        def decorated_function(*args, **kwargs):

            if not session.get("user_id"):

                flash(
                    "Please login first.",
                    "warning"
                )

                return redirect(
                    url_for("login")
                )

            if session.get("role") not in roles:

                flash(
                    "You do not have permission to access this page.",
                    "danger"
                )

                return redirect(
                    url_for("index")
                )

            return function(
                *args,
                **kwargs
            )

        return decorated_function

    return decorator


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    try:

        services = query(
            """
            SELECT
                s.*,
                u.name AS worker_name,
                u.phone AS worker_phone

            FROM services s

            LEFT JOIN users u
                ON u.id = s.worker_id

            WHERE s.is_active = 1

            ORDER BY s.id DESC

            LIMIT 8
            """,
            fetch=True
        )

    except Exception as error:

        print(
            "HOME ERROR:",
            error
        )

        services = []

    return render_template(
        "index.html",
        services=services
    )


# ============================================================
# SERVICES
# ============================================================

@app.route("/services")
def services():

    keyword = request.args.get(
        "q",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    sql = """
        SELECT
            s.*,
            u.name AS worker_name,
            u.phone AS worker_phone

        FROM services s

        LEFT JOIN users u
            ON u.id = s.worker_id

        WHERE s.is_active = 1
    """

    params = []

    if keyword:

        sql += """
            AND (
                s.name LIKE %s
                OR s.description LIKE %s
                OR s.category LIKE %s
            )
        """

        value = f"%{keyword}%"

        params.extend([
            value,
            value,
            value
        ])

    if category:

        sql += """
            AND s.category = %s
        """

        params.append(category)

    sql += """
        ORDER BY s.id DESC
    """

    try:

        services_list = query(
            sql,
            tuple(params),
            fetch=True
        )

        categories = query(
            """
            SELECT DISTINCT category

            FROM services

            WHERE category IS NOT NULL
              AND category <> ''

            ORDER BY category
            """,
            fetch=True
        )

    except Exception as error:

        print(
            "SERVICES ERROR:",
            error
        )

        services_list = []
        categories = []

    return render_template(
        "services.html",
        services=services_list,
        categories=categories,
        keyword=keyword,
        selected_category=category
    )


# ============================================================
# SERVICE DETAILS
# ============================================================

@app.route(
    "/service/<int:service_id>"
)
def service_detail(service_id):

    service = query(
        """
        SELECT
            s.*,

            u.name AS worker_name,
            u.phone AS worker_phone,
            u.location AS worker_location,
            u.latitude AS worker_latitude,
            u.longitude AS worker_longitude

        FROM services s

        LEFT JOIN users u
            ON u.id = s.worker_id

        WHERE s.id = %s

        LIMIT 1
        """,
        (service_id,),
        fetchone=True
    )

    if not service:

        flash(
            "Service not found.",
            "danger"
        )

        return redirect(
            url_for("services")
        )

    return render_template(
        "service_detail.html",
        service=service
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            "customer"
        )

        if role not in [
            "customer",
            "worker"
        ]:

            role = "customer"

        if not name or not email or not password:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        try:

            existing = query(
                """
                SELECT id

                FROM users

                WHERE email = %s

                LIMIT 1
                """,
                (email,),
                fetchone=True
            )

            if existing:

                flash(
                    "Email is already registered.",
                    "danger"
                )

                return render_template(
                    "register.html"
                )

            password_hash = generate_password_hash(
                password
            )

            query(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    phone,
                    password,
                    role
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    name,
                    email,
                    phone,
                    password_hash,
                    role
                )
            )

            flash(
                "Registration successful. Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as error:

            print(
                "REGISTER ERROR:",
                error
            )

            flash(
                "Registration failed. Check your database.",
                "danger"
            )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        try:

            user = query(
                """
                SELECT *

                FROM users

                WHERE email = %s

                LIMIT 1
                """,
                (email,),
                fetchone=True
            )

        except Exception as error:

            print(
                "LOGIN ERROR:",
                error
            )

            flash(
                "Database error during login.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        if not user:

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        try:

            valid = check_password_hash(
                user["password"],
                password
            )

        except Exception as error:

            print(
                "PASSWORD ERROR:",
                error
            )

            valid = False

        if not valid:

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        session.clear()

        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        flash(
            f"Welcome, {user['name']}!",
            "success"
        )

        if user["role"] == "worker":

            return redirect(
                url_for("worker_dashboard")
            )

        if user["role"] == "admin":

            return redirect(
                url_for("admin_dashboard")
            )

        return redirect(
            url_for("customer_dashboard")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# ============================================================
# CUSTOMER DASHBOARD
# ============================================================

@app.route("/customer")
@login_required
@role_required("customer")
def customer_dashboard():

    try:

        user = query(
            """
            SELECT
                id,
                name,
                email,
                phone,
                role,
                location,
                city,
                latitude,
                longitude

            FROM users

            WHERE id = %s

            LIMIT 1
            """,
            (session["user_id"],),
            fetchone=True
        )

        bookings = query(
            """
            SELECT
                b.*,

                s.name AS service_name,
                s.price AS price,

                u.name AS worker_name,
                u.phone AS worker_phone,
                u.location AS worker_location,
                u.latitude AS worker_latitude,
                u.longitude AS worker_longitude

            FROM bookings b

            LEFT JOIN services s
                ON s.id = b.service_id

            LEFT JOIN users u
                ON u.id = b.worker_id

            WHERE b.customer_id = %s

            ORDER BY b.id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

    except Exception as error:

        print(
            "CUSTOMER DASHBOARD ERROR:",
            error
        )

        user = None
        bookings = []

    return render_template(
        "customer_dashboard.html",
        user=user,
        bookings=bookings
    )


# ============================================================
# CUSTOMER LOCATION
# ============================================================

@app.route(
    "/customer/location",
    methods=["POST"]
)
@login_required
@role_required("customer")
def save_customer_location():

    location = request.form.get(
        "location",
        ""
    ).strip()

    city = request.form.get(
        "city",
        ""
    ).strip()

    latitude = request.form.get(
        "latitude",
        ""
    ).strip()

    longitude = request.form.get(
        "longitude",
        ""
    ).strip()

    try:

        latitude = (
            float(latitude)
            if latitude
            else None
        )

        longitude = (
            float(longitude)
            if longitude
            else None
        )

    except ValueError:

        flash(
            "Invalid latitude or longitude.",
            "danger"
        )

        return redirect(
            url_for("customer_dashboard")
        )

    try:

        query(
            """
            UPDATE users

            SET
                location = %s,
                city = %s,
                latitude = %s,
                longitude = %s

            WHERE id = %s
            """,
            (
                location,
                city,
                latitude,
                longitude,
                session["user_id"]
            )
        )

        flash(
            "Customer location saved.",
            "success"
        )

    except Exception as error:

        print(
            "CUSTOMER LOCATION ERROR:",
            error
        )

        flash(
            "Unable to save location.",
            "danger"
        )

    return redirect(
        url_for("customer_dashboard")
    )


# ============================================================
# BOOK SERVICE
# ============================================================
@app.route(
    "/book/<int:service_id>",
    methods=["GET", "POST"]
)
@login_required
@role_required("customer")
def book_service(service_id):

    # ========================================================
    # GET SERVICE + WORKER
    # ========================================================

    service = query(
        """
        SELECT
            s.*,

            u.name AS worker_name,
            u.phone AS worker_phone,
            u.location AS worker_location,
            u.latitude AS worker_latitude,
            u.longitude AS worker_longitude

        FROM services s

        LEFT JOIN users u
            ON u.id = s.worker_id

        WHERE s.id = %s
          AND s.is_active = 1

        LIMIT 1
        """,
        (service_id,),
        fetchone=True
    )

    if not service:

        flash(
            "Service not found.",
            "danger"
        )

        return redirect(
            url_for("services")
        )

    # ========================================================
    # GET CUSTOMER
    # ========================================================

    customer = query(
        """
        SELECT *

        FROM users

        WHERE id = %s

        LIMIT 1
        """,
        (session["user_id"],),
        fetchone=True
    )

    if not customer:

        session.clear()

        flash(
            "Please login again.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    # ========================================================
    # POST BOOKING
    # ========================================================

    if request.method == "POST":

        booking_date = request.form.get(
            "booking_date",
            ""
        ).strip()

        booking_time = request.form.get(
            "booking_time",
            ""
        ).strip()

        customer_phone = request.form.get(
            "customer_phone",
            ""
        ).strip()

        customer_location = request.form.get(
            "customer_location",
            ""
        ).strip()

        customer_latitude = request.form.get(
            "customer_latitude",
            ""
        ).strip()

        customer_longitude = request.form.get(
            "customer_longitude",
            ""
        ).strip()

        # ====================================================
        # VALIDATION
        # ====================================================

        if not booking_date:

            flash(
                "Please select booking date.",
                "danger"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        if not booking_time:

            flash(
                "Please select booking time.",
                "danger"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        # ====================================================
        # CUSTOMER PHONE
        # ====================================================

        if not customer_phone:

            customer_phone = customer.get(
                "phone",
                ""
            )

        if not customer_phone:

            flash(
                "Please enter your phone number.",
                "danger"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        # ====================================================
        # CUSTOMER LOCATION
        # ====================================================

        if not customer_location:

            customer_location = customer.get(
                "location",
                ""
            )

        if not customer_location:

            flash(
                "Please enter your service location.",
                "danger"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        # ====================================================
        # GPS COORDINATES
        #
        # First use coordinates from booking form.
        # If empty, use coordinates saved in users table.
        # ====================================================

        if not customer_latitude:

            customer_latitude = customer.get(
                "latitude"
            )

        if not customer_longitude:

            customer_longitude = customer.get(
                "longitude"
            )

        # ====================================================
        # CONVERT GPS TO FLOAT
        # ====================================================

        try:

            if customer_latitude not in [
                None,
                ""
            ]:

                customer_latitude = float(
                    customer_latitude
                )

            else:

                customer_latitude = None

            if customer_longitude not in [
                None,
                ""
            ]:

                customer_longitude = float(
                    customer_longitude
                )

            else:

                customer_longitude = None

        except (
            TypeError,
            ValueError
        ):

            customer_latitude = None
            customer_longitude = None

        # ====================================================
        # REQUIRE GPS
        # ====================================================

        if (
            customer_latitude is None
            or customer_longitude is None
        ):

            flash(
                "Please click 'Use My Current Location' "
                "before confirming the booking.",
                "warning"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        # ====================================================
        # CREATE BOOKING
        # ====================================================

        try:

            query(
                """
                INSERT INTO bookings
                (
                    customer_id,
                    service_id,
                    worker_id,
                    booking_date,
                    booking_time,
                    customer_phone,
                    customer_location,
                    customer_latitude,
                    customer_longitude,
                    status,
                    payment_status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    service_id,
                    service["worker_id"],
                    booking_date,
                    booking_time,
                    customer_phone,
                    customer_location,
                    customer_latitude,
                    customer_longitude,
                    "Pending",
                    "Pending"
                )
            )

        except Exception as error:

            print(
                "BOOKING ERROR:",
                error
            )

            flash(
                "Unable to create booking. "
                "Check the terminal for the MySQL error.",
                "danger"
            )

            return render_template(
                "booking.html",
                service=service,
                customer=customer
            )

        # ====================================================
        # SAVE GPS TO CUSTOMER PROFILE TOO
        # ====================================================

        try:

            query(
                """
                UPDATE users

                SET
                    location = %s,
                    latitude = %s,
                    longitude = %s

                WHERE id = %s
                """,
                (
                    customer_location,
                    customer_latitude,
                    customer_longitude,
                    session["user_id"]
                )
            )

        except Exception as error:

            print(
                "CUSTOMER GPS PROFILE UPDATE ERROR:",
                error
            )

        # ====================================================
        # WORKER NOTIFICATION
        # ====================================================

        try:

            query(
                """
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    notification_type
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    service["worker_id"],
                    "New Booking",
                    f"New booking for {service['name']}.",
                    "booking"
                )
            )

        except Exception as error:

            print(
                "NOTIFICATION ERROR:",
                error
            )

        # ====================================================
        # SUCCESS
        # ====================================================

        flash(
            "Booking created successfully. "
            "Waiting for worker approval.",
            "success"
        )

        return redirect(
            url_for("my_bookings")
        )

    # ========================================================
    # GET BOOKING PAGE
    # ========================================================

    return render_template(
        "booking.html",
        service=service,
        customer=customer
    )
# ============================================================
# MY BOOKINGS
# ============================================================

@app.route("/my-bookings")
@login_required
@role_required("customer")
def my_bookings():

    try:

        bookings = query(
            """
            SELECT
                b.*,

                s.name AS service_name,
                s.description AS service_description,
                s.category AS service_category,
                s.price AS price,

                u.name AS worker_name,
                u.phone AS worker_phone,
                u.location AS worker_location,
                u.latitude AS worker_latitude,
                u.longitude AS worker_longitude

            FROM bookings b

            LEFT JOIN services s
                ON s.id = b.service_id

            LEFT JOIN users u
                ON u.id = b.worker_id

            WHERE b.customer_id = %s

            ORDER BY b.id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

    except Exception as error:

        print(
            "MY BOOKINGS ERROR:",
            error
        )

        bookings = []

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )


# ============================================================
# PAYMENT PAGE
# ============================================================

@app.route(
    "/payment/<int:booking_id>"
)
@login_required
@role_required("customer")
def payment_page(booking_id):

    booking = query(
        """
        SELECT
            b.*,

            s.name AS service_name,
            s.description AS service_description,
            s.price AS price,

            u.name AS worker_name,
            u.phone AS worker_phone

        FROM bookings b

        LEFT JOIN services s
            ON s.id = b.service_id

        LEFT JOIN users u
            ON u.id = b.worker_id

        WHERE b.id = %s
          AND b.customer_id = %s

        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("my_bookings")
        )

    if booking.get("payment_status") == "Paid":

        flash(
            "Booking already paid.",
            "info"
        )

        return redirect(
            url_for("my_bookings")
        )

    return render_template(
        "payment.html",
        booking=booking
    )
# ============================================================
# PAYMENT SUCCESS
# ============================================================

@app.route(
    "/payment/success/<int:booking_id>",
    methods=["GET", "POST"]
)
@login_required
@role_required("customer")
def payment_success(booking_id):

    booking = query(
        """
        SELECT *
        FROM bookings
        WHERE id = %s
          AND customer_id = %s
        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        if request.method == "POST":
            return jsonify({
                "success": False,
                "message": "Booking not found."
            }), 404

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("my_bookings")
        )


    try:

        query(
            """
            UPDATE bookings
            SET payment_status = %s
            WHERE id = %s
              AND customer_id = %s
            """,
            (
                "Paid",
                booking_id,
                session["user_id"]
            )
        )

        # POST request from Razorpay JavaScript
        if request.method == "POST":

            return jsonify({
                "success": True,
                "message": "Payment successful."
            })


        # GET request
        flash(
            "Payment successful!",
            "success"
        )

        return redirect(
            url_for("my_bookings")
        )


    except Exception as error:

        print(
            "PAYMENT UPDATE ERROR:",
            error
        )

        if request.method == "POST":

            return jsonify({
                "success": False,
                "message": "Unable to update payment."
            }), 500

        flash(
            "Unable to update payment.",
            "danger"
        )

        return redirect(
            url_for("my_bookings")
        )



# ============================================================
# BOOKING MAP
# ============================================================

@app.route(
    "/booking-map/<int:booking_id>"
)
@login_required
def booking_map(booking_id):

    booking = query(
        """
        SELECT
            b.*,

            s.name AS service_name,
            s.price AS price,

            c.name AS customer_name,
            c.phone AS customer_phone,
            c.location AS customer_location,
            c.latitude AS customer_latitude,
            c.longitude AS customer_longitude,

            w.name AS worker_name,
            w.phone AS worker_phone,
            w.location AS worker_location,
            w.latitude AS worker_latitude,
            w.longitude AS worker_longitude

        FROM bookings b

        LEFT JOIN services s
            ON s.id = b.service_id

        LEFT JOIN users c
            ON c.id = b.customer_id

        LEFT JOIN users w
            ON w.id = b.worker_id

        WHERE b.id = %s

        LIMIT 1
        """,
        (booking_id,),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("index")
        )

    if session["user_id"] not in [
        booking["customer_id"],
        booking["worker_id"]
    ]:

        flash(
            "You cannot access this map.",
            "danger"
        )

        return redirect(
            url_for("index")
        )

    return render_template(
        "booking_map.html",
        booking=booking
    )


# ============================================================
# RATE SERVICE
# ============================================================

@app.route(
    "/rate/<int:booking_id>",
    methods=["GET", "POST"]
)
@login_required
@role_required("customer")
def rate_service(booking_id):

    booking = query(
        """
        SELECT
            b.*,

            s.name AS service_name,
            s.price AS price,

            u.name AS worker_name

        FROM bookings b

        LEFT JOIN services s
            ON s.id = b.service_id

        LEFT JOIN users u
            ON u.id = b.worker_id

        WHERE b.id = %s
          AND b.customer_id = %s

        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("my_bookings")
        )

    if booking["status"] != "Completed":

        flash(
            "Rating is available after work is completed.",
            "warning"
        )

        return redirect(
            url_for("my_bookings")
        )

    try:

        existing = query(
            """
            SELECT id

            FROM ratings

            WHERE booking_id = %s
              AND customer_id = %s

            LIMIT 1
            """,
            (
                booking_id,
                session["user_id"]
            ),
            fetchone=True
        )

    except Exception as error:

        print(
            "RATING CHECK ERROR:",
            error
        )

        existing = None

    if existing:

        flash(
            "You have already rated this service.",
            "info"
        )

        return redirect(
            url_for("my_bookings")
        )

    if request.method == "POST":

        rating = request.form.get(
            "rating",
            ""
        ).strip()

        review = request.form.get(
            "review",
            ""
        ).strip()

        try:

            rating = int(rating)

            if rating < 1 or rating > 5:

                raise ValueError

        except ValueError:

            flash(
                "Rating must be between 1 and 5.",
                "danger"
            )

            return render_template(
                "rating.html",
                booking=booking
            )

        try:

            query(
                """
                INSERT INTO ratings
                (
                    booking_id,
                    customer_id,
                    worker_id,
                    rating,
                    review
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    booking_id,
                    session["user_id"],
                    booking["worker_id"],
                    rating,
                    review
                )
            )

            flash(
                "Rating submitted successfully.",
                "success"
            )

            return redirect(
                url_for("my_bookings")
            )

        except Exception as error:

            print(
                "RATING ERROR:",
                error
            )

            flash(
                "Unable to submit rating.",
                "danger"
            )

    return render_template(
        "rating.html",
        booking=booking
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
@login_required
def profile():

    user = query(
        """
        SELECT *

        FROM users

        WHERE id = %s

        LIMIT 1
        """,
        (session["user_id"],),
        fetchone=True
    )

    return render_template(
        "profile.html",
        user=user
    )


# ============================================================
# WORKER DASHBOARD
# ============================================================

@app.route("/worker")
@login_required
@role_required("worker")
def worker_dashboard():

    try:

        services_list = query(
            """
            SELECT *

            FROM services

            WHERE worker_id = %s

            ORDER BY id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

        bookings = query(
            """
            SELECT
                b.*,

                s.name AS service_name,
                s.price AS price,

                u.name AS customer_name,
                u.phone AS customer_phone,
                u.location AS customer_location,
                u.latitude AS customer_latitude,
                u.longitude AS customer_longitude

            FROM bookings b

            LEFT JOIN services s
                ON s.id = b.service_id

            LEFT JOIN users u
                ON u.id = b.customer_id

            WHERE b.worker_id = %s

            ORDER BY b.id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

    except Exception as error:

        print(
            "WORKER DASHBOARD ERROR:",
            error
        )

        services_list = []
        bookings = []

    return render_template(
        "worker_dashboard.html",
        services=services_list,
        bookings=bookings
    )


# ============================================================
# ADD SERVICE
# ============================================================

@app.route(
    "/add-service",
    methods=["GET", "POST"]
)
@login_required
@role_required("worker")
def add_service():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        price = request.form.get(
            "price",
            ""
        ).strip()

        if not name:

            flash(
                "Service name is required.",
                "danger"
            )

            return render_template(
                "add_service.html"
            )

        try:

            price = float(price)

        except ValueError:

            flash(
                "Enter a valid price.",
                "danger"
            )

            return render_template(
                "add_service.html"
            )

        try:

            query(
                """
                INSERT INTO services
                (
                    name,
                    description,
                    category,
                    price,
                    worker_id,
                    is_active
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    name,
                    description,
                    category,
                    price,
                    session["user_id"],
                    1
                )
            )

            flash(
                "Service added successfully.",
                "success"
            )

            return redirect(
                url_for("worker_dashboard")
            )

        except Exception as error:

            print(
                "ADD SERVICE ERROR:",
                error
            )

            flash(
                "Unable to add service.",
                "danger"
            )

    return render_template(
        "add_service.html"
    )


# ============================================================
# WORKER LOCATION
# ============================================================

@app.route(
    "/worker/location",
    methods=["POST"]
)
@login_required
@role_required("worker")
def save_worker_location():

    location = request.form.get(
        "location",
        ""
    ).strip()

    city = request.form.get(
        "city",
        ""
    ).strip()

    latitude = request.form.get(
        "latitude",
        ""
    ).strip()

    longitude = request.form.get(
        "longitude",
        ""
    ).strip()

    try:

        latitude = (
            float(latitude)
            if latitude
            else None
        )

        longitude = (
            float(longitude)
            if longitude
            else None
        )

    except ValueError:

        flash(
            "Invalid coordinates.",
            "danger"
        )

        return redirect(
            url_for("worker_dashboard")
        )

    try:

        query(
            """
            UPDATE users

            SET
                location = %s,
                city = %s,
                latitude = %s,
                longitude = %s

            WHERE id = %s
            """,
            (
                location,
                city,
                latitude,
                longitude,
                session["user_id"]
            )
        )

        flash(
            "Worker location updated.",
            "success"
        )

    except Exception as error:

        print(
            "WORKER LOCATION ERROR:",
            error
        )

        flash(
            "Unable to update worker location.",
            "danger"
        )

    return redirect(
        url_for("worker_dashboard")
    )


# ============================================================
# WORKER ACCEPT BOOKING
# ============================================================
@app.route(
    "/worker/booking/<int:booking_id>/accept",
    methods=["POST"]
)
@login_required
@role_required("worker")
def accept_booking(booking_id):

    booking = query(
        """
        SELECT *
        FROM bookings
        WHERE id = %s
          AND worker_id = %s
        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("worker_dashboard")
        )

    try:

        # IMPORTANT:
        # Database status is Approved, NOT Accepted
        query(
            """
            UPDATE bookings
            SET status = %s
            WHERE id = %s
              AND worker_id = %s
            """,
            (
                "Approved",
                booking_id,
                session["user_id"]
            )
        )

        # Notify customer
        try:

            query(
                """
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    notification_type
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    booking["customer_id"],
                    "Booking Approved",
                    "Your worker has approved your booking.",
                    "booking"
                )
            )

        except Exception as notification_error:

            print(
                "NOTIFICATION ERROR:",
                notification_error
            )

        flash(
            "Booking approved successfully.",
            "success"
        )

    except Exception as error:

        print(
            "ACCEPT ERROR:",
            error
        )

        flash(
            "Unable to approve booking.",
            "danger"
        )

    return redirect(
        url_for("worker_dashboard")
    )

# ============================================================
# WORKER REJECT BOOKING
# ============================================================

@app.route(
    "/worker/booking/<int:booking_id>/reject",
    methods=["POST"]
)
@login_required
@role_required("worker")
def reject_booking(booking_id):

    booking = query(
        """
        SELECT *

        FROM bookings

        WHERE id = %s
          AND worker_id = %s

        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("worker_dashboard")
        )

    try:

        query(
            """
            UPDATE bookings

            SET status = %s

            WHERE id = %s
              AND worker_id = %s
            """,
            (
                "Rejected",
                booking_id,
                session["user_id"]
            )
        )

        try:

            query(
                """
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    notification_type
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    booking["customer_id"],
                    "Booking Rejected",
                    "Your worker rejected the booking.",
                    "booking"
                )
            )

        except Exception as error:

            print(
                "REJECT NOTIFICATION ERROR:",
                error
            )

        flash(
            "Booking rejected.",
            "success"
        )

    except Exception as error:

        print(
            "REJECT ERROR:",
            error
        )

        flash(
            "Unable to reject booking.",
            "danger"
        )

    return redirect(
        url_for("worker_dashboard")
    )


# ============================================================
# WORKER COMPLETE BOOKING
# ============================================================

@app.route(
    "/worker/booking/<int:booking_id>/complete",
    methods=["POST"]
)
@login_required
@role_required("worker")
def complete_booking(booking_id):

    booking = query(
        """
        SELECT *

        FROM bookings

        WHERE id = %s
          AND worker_id = %s

        LIMIT 1
        """,
        (
            booking_id,
            session["user_id"]
        ),
        fetchone=True
    )

    if not booking:

        flash(
            "Booking not found.",
            "danger"
        )

        return redirect(
            url_for("worker_dashboard")
        )

    try:

        query(
            """
            UPDATE bookings

            SET status = %s

            WHERE id = %s
              AND worker_id = %s
            """,
            (
                "Completed",
                booking_id,
                session["user_id"]
            )
        )

        try:

            query(
                """
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    notification_type
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    booking["customer_id"],
                    "Work Completed",
                    "Your worker completed the service.",
                    "booking"
                )
            )

        except Exception as error:

            print(
                "COMPLETE NOTIFICATION ERROR:",
                error
            )

        flash(
            "Work marked as completed.",
            "success"
        )

    except Exception as error:

        print(
            "COMPLETE ERROR:",
            error
        )

        flash(
            "Unable to complete booking.",
            "danger"
        )

    return redirect(
        url_for("worker_dashboard")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():

    try:

        users = query(
            """
            SELECT
                id,
                name,
                email,
                phone,
                role,
                city,
                location

            FROM users

            ORDER BY id DESC
            """,
            fetch=True
        )

        services_list = query(
            """
            SELECT
                s.*,
                u.name AS worker_name

            FROM services s

            LEFT JOIN users u
                ON u.id = s.worker_id

            ORDER BY s.id DESC
            """,
            fetch=True
        )

        bookings = query(
            """
            SELECT
                b.*,

                s.name AS service_name,

                c.name AS customer_name,

                w.name AS worker_name

            FROM bookings b

            LEFT JOIN services s
                ON s.id = b.service_id

            LEFT JOIN users c
                ON c.id = b.customer_id

            LEFT JOIN users w
                ON w.id = b.worker_id

            ORDER BY b.id DESC
            """,
            fetch=True
        )

        stats = {
            "users": len(users),
            "services": len(services_list),
            "bookings": len(bookings)
        }

    except Exception as error:

        print(
            "ADMIN ERROR:",
            error
        )

        users = []
        services_list = []
        bookings = []

        stats = {
            "users": 0,
            "services": 0,
            "bookings": 0
        }

    return render_template(
        "admin_dashboard.html",
        users=users,
        services=services_list,
        bookings=bookings,
        stats=stats
    )


# ============================================================
# ADMIN USERS
# ============================================================

@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():

    users = query(
        """
        SELECT *

        FROM users

        ORDER BY id DESC
        """,
        fetch=True
    )

    return render_template(
        "admin_users.html",
        users=users
    )


# ============================================================
# ADMIN BOOKINGS
# ============================================================

@app.route("/admin/bookings")
@login_required
@role_required("admin")
def admin_bookings():

    bookings = query(
        """
        SELECT
            b.*,

            s.name AS service_name,

            c.name AS customer_name,
            c.phone AS customer_phone,

            w.name AS worker_name,
            w.phone AS worker_phone

        FROM bookings b

        LEFT JOIN services s
            ON s.id = b.service_id

        LEFT JOIN users c
            ON c.id = b.customer_id

        LEFT JOIN users w
            ON w.id = b.worker_id

        ORDER BY b.id DESC
        """,
        fetch=True
    )

    return render_template(
        "admin_bookings.html",
        bookings=bookings
    )


# ============================================================
# ADMIN SERVICES
# ============================================================

@app.route("/admin/services")
@login_required
@role_required("admin")
def admin_services():

    services_list = query(
        """
        SELECT
            s.*,
            u.name AS worker_name

        FROM services s

        LEFT JOIN users u
            ON u.id = s.worker_id

        ORDER BY s.id DESC
        """,
        fetch=True
    )

    return render_template(
        "admin_services.html",
        services=services_list
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
@login_required
def notifications():

    try:

        notifications_list = query(
            """
            SELECT *

            FROM notifications

            WHERE user_id = %s

            ORDER BY id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

    except Exception as error:

        print(
            "NOTIFICATION ERROR:",
            error
        )

        notifications_list = []

    return render_template(
        "notifications.html",
        notifications=notifications_list
    )

# ============================================================
# WORKER MESSAGES
# ============================================================

@app.route("/worker/messages")
@login_required
@role_required("worker")
def worker_messages():

    try:
        messages = query(
            """
            SELECT
                m.*,
                u.name AS customer_name,
                u.phone AS customer_phone,
                s.name AS service_name
            FROM messages m

            LEFT JOIN users u
                ON u.id = m.sender_id

            LEFT JOIN bookings b
                ON b.id = m.booking_id

            LEFT JOIN services s
                ON s.id = b.service_id

            WHERE m.receiver_id = %s

            ORDER BY m.id DESC
            """,
            (session["user_id"],),
            fetch=True
        )

    except Exception as error:

        print("WORKER MESSAGES ERROR:", error)

        messages = []

        flash(
            "Unable to load messages.",
            "danger"
        )

    return render_template(
        "worker_messages.html",
        messages=messages
    )


# ============================================================
# WORKER REPLY MESSAGE
# ============================================================

@app.route(
    "/worker/messages/reply/<int:message_id>",
    methods=["POST"]
)
@login_required
@role_required("worker")
def worker_reply_message(message_id):

    reply = request.form.get(
        "reply",
        ""
    ).strip()

    if not reply:

        flash(
            "Please enter a reply.",
            "danger"
        )

        return redirect(
            url_for("worker_messages")
        )

    try:

        original_message = query(
            """
            SELECT
                m.*,
                b.worker_id,
                b.customer_id
            FROM messages m

            LEFT JOIN bookings b
                ON b.id = m.booking_id

            WHERE m.id = %s

            LIMIT 1
            """,
            (message_id,),
            fetchone=True
        )

        if not original_message:

            flash(
                "Message not found.",
                "danger"
            )

            return redirect(
                url_for("worker_messages")
            )

        # Security: this worker must own the booking
        if int(original_message["worker_id"]) != int(
            session["user_id"]
        ):

            flash(
                "You are not allowed to reply to this message.",
                "danger"
            )

            return redirect(
                url_for("worker_messages")
            )

        query(
            """
            INSERT INTO messages
            (
                booking_id,
                sender_id,
                receiver_id,
                message
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                original_message["booking_id"],
                session["user_id"],
                original_message["customer_id"],
                reply
            )
        )

        flash(
            "Reply sent successfully.",
            "success"
        )

    except Exception as error:

        print(
            "WORKER REPLY ERROR:",
            error
        )

        flash(
            "Unable to send reply.",
            "danger"
        )

    return redirect(
        url_for("worker_messages")
    )


# ============================================================
# WORKER RATINGS
# ============================================================

@app.route("/worker/ratings")
@login_required
@role_required("worker")
def worker_ratings():

    worker_id = session["user_id"]

    try:

        ratings = query(
            """
            SELECT
                r.*,

                b.id AS booking_id,

                s.name AS service_name,

                u.name AS customer_name

            FROM ratings r

            INNER JOIN bookings b
                ON b.id = r.booking_id

            INNER JOIN services s
                ON s.id = b.service_id

            INNER JOIN users u
                ON u.id = r.customer_id

            WHERE b.worker_id = %s

            ORDER BY r.id DESC
            """,
            (worker_id,),
            fetch=True
        )

    except Exception as error:

        print(
            "WORKER RATINGS ERROR:",
            error
        )

        ratings = []

        flash(
            "Unable to load ratings.",
            "danger"
        )

    return render_template(
        "worker_ratings.html",
        ratings=ratings
    )
#====adview===
@app.route("/admin/reviews")
@login_required

def admin_reviews():

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.id,
                r.rating,
                r.review,
                r.created_at,
                u.name AS customer_name,
                s.name AS service_name
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN services s ON r.service_id = s.id
            ORDER BY r.id DESC
        """)

        reviews = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "admin_reviews.html",
            reviews=reviews
        )

    except Exception as e:
        print("Admin reviews error:", e)
        return render_template(
            "admin_reviews.html",
            reviews=[]
        )
# ============================================================
# CUSTOMER MESSAGE WORKER
# ============================================================

@app.route(
    "/message-worker/<int:booking_id>",
    methods=["GET", "POST"]
)
@login_required
@role_required("customer")
def message_worker(booking_id):

    customer_id = session["user_id"]

    try:

        # ====================================================
        # GET BOOKING
        # ====================================================

        booking = query(
            """
            SELECT
                b.id,
                b.customer_id,
                b.service_id,
                b.worker_id,
                b.status,

                s.name AS service_name,

                u.name AS worker_name,
                u.phone AS worker_phone

            FROM bookings b

            LEFT JOIN services s
                ON s.id = b.service_id

            LEFT JOIN users u
                ON u.id = b.worker_id

            WHERE b.id = %s
              AND b.customer_id = %s

            LIMIT 1
            """,
            (
                booking_id,
                customer_id
            ),
            fetchone=True
        )

        # ====================================================
        # BOOKING NOT FOUND
        # ====================================================

        if not booking:

            flash(
                "Booking not found.",
                "danger"
            )

            return redirect(
                url_for("my_bookings")
            )

        # ====================================================
        # SEND MESSAGE
        # ====================================================

        if request.method == "POST":

            message_text = request.form.get(
                "message",
                ""
            ).strip()

            if not message_text:

                flash(
                    "Please enter a message.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "message_worker",
                        booking_id=booking_id
                    )
                )

            query(
                """
                INSERT INTO messages
                (
                    booking_id,
                    sender_id,
                    receiver_id,
                    message
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    booking_id,
                    customer_id,
                    booking["worker_id"],
                    message_text
                )
            )

            flash(
                "Message sent to the worker.",
                "success"
            )

            return redirect(
                url_for(
                    "message_worker",
                    booking_id=booking_id
                )
            )

        # ====================================================
        # LOAD CONVERSATION
        # ====================================================

        messages = query(
            """
            SELECT
                m.id,
                m.booking_id,
                m.sender_id,
                m.receiver_id,
                m.message,

                sender.name AS sender_name,

                receiver.name AS receiver_name

            FROM messages m

            LEFT JOIN users sender
                ON sender.id = m.sender_id

            LEFT JOIN users receiver
                ON receiver.id = m.receiver_id

            WHERE m.booking_id = %s

            ORDER BY m.id ASC
            """,
            (booking_id,),
            fetch=True
        )

        return render_template(
            "message_worker.html",
            booking=booking,
            messages=messages
        )

    except Exception as error:

        print(
            "MESSAGE WORKER ERROR:",
            error
        )

        flash(
            "Unable to load messaging.",
            "danger"
        )

        return redirect(
            url_for("my_bookings")
        )   
# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    try:

        result = query(
            "SELECT 1 AS ok",
            fetchone=True
        )

        return jsonify({
            "status": "healthy",
            "database": result["ok"] == 1
        })

    except Exception as error:

        return jsonify({
            "status": "error",
            "database": False,
            "error": str(error)
        }), 500


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return render_template(
        "404.html"
    ), 404


# ============================================================
# 500
# ============================================================

@app.errorhandler(500)
def internal_error(error):

    print(
        "500 ERROR:",
        error
    )

    return render_template(
        "500.html"
    ), 500


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AI SERVICE HUB")
    print("=" * 60)

    print(
        "Database:",
        getattr(
            Config,
            "MYSQL_DATABASE",
            "Unknown"
        )
    )

    print(
        "Server:",
        "http://127.0.0.1:5000"
    )

    print("=" * 60)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )