
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import func
import os
from datetime import datetime
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///academy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'avi', 'mov', 'wmv', 'txt', 'docx', 'pptx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Create upload directory
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# SQLAlchemy Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = relationship('Enrollment', back_populates='user', cascade='all, delete-orphan')
    evaluations = relationship('Evaluation', back_populates='user', cascade='all, delete-orphan')
    managed_courses = relationship('Course', back_populates='manager', foreign_keys='Course.manager_id')

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructor = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    price = db.Column(db.String(20))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    enrollments = relationship('Enrollment', back_populates='course', cascade='all, delete-orphan')
    evaluations = relationship('Evaluation', back_populates='course', cascade='all, delete-orphan')
    files = relationship('CourseFile', back_populates='course', cascade='all, delete-orphan')
    manager = relationship('User', back_populates='managed_courses', foreign_keys=[manager_id])

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='enrollments')
    course = relationship('Course', back_populates='enrollments')

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='evaluations')
    course = relationship('Course', back_populates='evaluations')
    
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5'),
    )

class CourseFile(db.Model):
    __tablename__ = 'course_files'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = relationship('Course', back_populates='files')

def init_db():
    with app.app_context():
        db.create_all()
        
        # Insert default admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
            admin = User(
                username='admin',
                password=admin_password,
                email='admin@aiacademy.com',
                role='admin'
            )
            db.session.add(admin)
        
        # Insert dummy student user
        student = User.query.filter_by(username='student_demo').first()
        if not student:
            student_password = hashlib.sha256('student123'.encode()).hexdigest()
            student = User(
                username='student_demo',
                password=student_password,
                email='student@aiacademy.com',
                role='student'
            )
            db.session.add(student)
        
        # Insert sample courses if none exist
        if Course.query.count() == 0:
            sample_courses = [
                Course(
                    title='Introduction to AI',
                    description='Learn the fundamentals of Artificial Intelligence.',
                    instructor='Jane Smith',
                    duration='6 hours',
                    price='$49',
                    content='Complete AI fundamentals course content',
                    manager_id=admin.id
                ),
                Course(
                    title='Machine Learning Basics',
                    description='Explore the basics of machine learning algorithms.',
                    instructor='Sarah Johnson',
                    duration='8 hours',
                    price='$59',
                    content='ML algorithms and practical examples',
                    manager_id=admin.id
                ),
                Course(
                    title='Deep Learning with Python',
                    description='Hands-on deep learning with Python frameworks.',
                    instructor='Mike Chen',
                    duration='7 hours',
                    price='$39',
                    content='Deep learning with TensorFlow and PyTorch',
                    manager_id=admin.id
                ),
                Course(
                    title='Neural Networks and NLP',
                    description='Learn about neural networks and natural language processing.',
                    instructor='Emily Davis',
                    duration='11 hours',
                    price='$69',
                    content='Advanced NLP techniques and neural networks',
                    manager_id=admin.id
                )
            ]
            
            for course in sample_courses:
                db.session.add(course)
        
        db.session.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_file_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def require_login(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def require_admin(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Initialize database
init_db()

@app.route('/')
def home():
    courses = Course.query.limit(2).all()
    return render_template('home.html', courses=courses)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/instructors')
def instructors():
    # Get instructors with their course data and statistics
    instructors_query = db.session.query(
        Course.instructor,
        func.count(Course.id).label('course_count'),
        func.count(Enrollment.id).label('total_students'),
        func.avg(Evaluation.rating).label('avg_rating')
    ).outerjoin(Enrollment).outerjoin(Evaluation).group_by(Course.instructor).all()
    
    instructors_data = []
    for instructor_info in instructors_query:
        # Get courses for this instructor
        instructor_courses = Course.query.filter_by(instructor=instructor_info.instructor).all()
        
        instructors_data.append({
            'instructor': instructor_info.instructor,
            'course_count': instructor_info.course_count,
            'total_students': instructor_info.total_students or 0,
            'avg_rating': instructor_info.avg_rating,
            'courses': instructor_courses
        })
    
    return render_template('instructors.html', instructors_data=instructors_data)

@app.route('/courses')
def courses():
    # Get search and filter parameters
    search = request.args.get('search', '')
    instructor_filter = request.args.get('instructor', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    min_rating = request.args.get('min_rating', '')
    sort_by = request.args.get('sort_by', 'title')
    
    # Build query with relationships
    query = db.session.query(
        Course,
        func.avg(Evaluation.rating).label('avg_rating'),
        func.count(Evaluation.rating).label('rating_count'),
        func.count(Enrollment.id).label('enrollment_count')
    ).outerjoin(Evaluation).outerjoin(Enrollment).group_by(Course.id)
    
    if search:
        query = query.filter(
            db.or_(
                Course.title.like(f'%{search}%'),
                Course.description.like(f'%{search}%')
            )
        )
    
    if instructor_filter:
        query = query.filter(Course.instructor.like(f'%{instructor_filter}%'))
    
    if min_rating:
        query = query.having(func.avg(Evaluation.rating) >= float(min_rating))
    
    # Add sorting
    if sort_by == 'rating':
        query = query.order_by(func.avg(Evaluation.rating).desc())
    elif sort_by == 'price_low':
        query = query.order_by(Course.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Course.price.desc())
    elif sort_by == 'popular':
        query = query.order_by(func.count(Enrollment.id).desc())
    else:
        query = query.order_by(Course.title.asc())
    
    courses_data = query.all()
    
    # Get all instructors for filter dropdown
    instructors = db.session.query(Course.instructor).distinct().order_by(Course.instructor).all()
    
    return render_template('courses.html', 
                         courses_data=courses_data, 
                         instructors=instructors,
                         current_search=search,
                         current_instructor=instructor_filter,
                         current_min_price=min_price,
                         current_max_price=max_price,
                         current_min_rating=min_rating,
                         current_sort=sort_by)

@app.route('/browse-courses')
def browse_courses():
    courses = Course.query.all()
    return render_template('browse_courses.html', courses=courses)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')
        
        # Create new user
        hashed_password = hash_password(password)
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        user = User.query.filter_by(username=username, password=hashed_password).first()
        
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('home'))

@app.route('/dashboard')
@require_login
def dashboard():
    if session['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    # Get user's enrolled courses using relationships
    user = User.query.get(session['user_id'])
    enrollments = user.enrollments
    
    # Get recommended courses
    recommendations = get_recommendations(session['user_id'])
    
    return render_template('dashboard.html', enrollments=enrollments, recommendations=recommendations)

@app.route('/admin')
@require_admin
def admin_dashboard():
    # Get statistics using SQLAlchemy
    total_users = User.query.count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    
    # Get recent activities using relationships
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_evaluations = Evaluation.query.join(User).join(Course).order_by(Evaluation.created_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         total_users=total_users,
                         total_courses=total_courses,
                         total_enrollments=total_enrollments,
                         recent_users=recent_users,
                         recent_evaluations=recent_evaluations)

@app.route('/download/<int:file_id>')
@require_login
def download_file(file_id):
    # Get file info using relationships
    file_info = CourseFile.query.get_or_404(file_id)
    
    # Check if user is enrolled in this course
    enrollment = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=file_info.course_id
    ).first()
    
    if not enrollment and session['role'] != 'admin':
        flash('You must be enrolled in this course to download files')
        return redirect(url_for('course_detail', course_id=file_info.course_id))
    
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], file_info.filename, 
                                 as_attachment=True, download_name=file_info.original_filename)
    except FileNotFoundError:
        flash('File not found on server')
        return redirect(url_for('course_detail', course_id=file_info.course_id))

@app.route('/admin/courses/<int:course_id>/files')
@require_admin
def manage_course_files(course_id):
    course = Course.query.get_or_404(course_id)
    files = course.files  # Using relationship
    return render_template('manage_course_files.html', course=course, files=files, format_file_size=format_file_size)

@app.route('/admin/courses/<int:course_id>/upload', methods=['POST'])
@require_admin
def upload_course_files(course_id):
    uploaded_files = request.files.getlist('course_files')
    
    for file in uploaded_files:
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            unique_filename = timestamp + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)
            file_type = filename.rsplit('.', 1)[1].lower()
            
            # Create CourseFile using SQLAlchemy
            course_file = CourseFile(
                course_id=course_id,
                filename=unique_filename,
                original_filename=filename,
                file_type=file_type,
                file_size=file_size
            )
            db.session.add(course_file)
    
    db.session.commit()
    flash('Files uploaded successfully!')
    return redirect(url_for('manage_course_files', course_id=course_id))

@app.route('/admin/delete-file/<int:file_id>')
@require_admin
def delete_course_file(file_id):
    file_info = CourseFile.query.get_or_404(file_id)
    course_id = file_info.course_id
    
    # Delete from filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    db.session.delete(file_info)
    db.session.commit()
    flash('File deleted successfully!')
    
    return redirect(url_for('manage_course_files', course_id=course_id))

@app.route('/admin/courses')
@require_admin
def admin_courses():
    # Get courses managed by current admin
    admin_user = User.query.get(session['user_id'])
    courses = admin_user.managed_courses  # Using relationship
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/courses/add', methods=['GET', 'POST'])
@require_admin
def add_course():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        instructor = request.form['instructor']
        duration = request.form['duration']
        price = request.form['price']
        content = request.form['content']
        
        # Create course with current admin as manager
        course = Course(
            title=title,
            description=description,
            instructor=instructor,
            duration=duration,
            price=price,
            content=content,
            manager_id=session['user_id']
        )
        db.session.add(course)
        db.session.flush()  # To get the course ID
        
        # Handle file uploads
        uploaded_files = request.files.getlist('course_files')
        for file in uploaded_files:
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                file_size = os.path.getsize(file_path)
                file_type = filename.rsplit('.', 1)[1].lower()
                
                course_file = CourseFile(
                    course_id=course.id,
                    filename=unique_filename,
                    original_filename=filename,
                    file_type=file_type,
                    file_size=file_size
                )
                db.session.add(course_file)
        
        db.session.commit()
        flash('Course added successfully!')
        return redirect(url_for('admin_courses'))
    
    return render_template('add_course.html')

@app.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@require_admin
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if current admin manages this course
    if course.manager_id != session['user_id'] and session['role'] != 'admin':
        flash('You can only edit courses you manage')
        return redirect(url_for('admin_courses'))
    
    if request.method == 'POST':
        course.title = request.form['title']
        course.description = request.form['description']
        course.instructor = request.form['instructor']
        course.duration = request.form['duration']
        course.price = request.form['price']
        course.content = request.form['content']
        
        db.session.commit()
        flash('Course updated successfully!')
        return redirect(url_for('admin_courses'))
    
    return render_template('edit_course.html', course=course)

@app.route('/enroll/<int:course_id>')
@require_login
def enroll(course_id):
    # Redirect to confirmation page instead of direct enrollment
    return redirect(url_for('confirm_enrollment', course_id=course_id))

@app.route('/confirm-enrollment/<int:course_id>')
@require_login
def confirm_enrollment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if existing:
        flash('You are already enrolled in this course')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Get course statistics
    stats = db.session.query(
        func.avg(Evaluation.rating).label('avg_rating'),
        func.count(Evaluation.rating).label('rating_count'),
        func.count(Enrollment.id).label('enrollment_count')
    ).select_from(Course).outerjoin(Evaluation).outerjoin(Enrollment).filter(
        Course.id == course_id
    ).first()
    
    return render_template('confirm_enrollment.html', 
                         course=course,
                         avg_rating=stats.avg_rating,
                         rating_count=stats.rating_count or 0,
                         enrollment_count=stats.enrollment_count or 0)

@app.route('/payment/<int:course_id>')
@require_login
def payment_page(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if existing:
        flash('You are already enrolled in this course')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Calculate total price
    if course.price == 'Free':
        return redirect(url_for('process_enrollment', course_id=course_id))
    
    course_price = float(course.price.replace('$', ''))
    platform_fee = 2.99
    total_price = round(course_price + platform_fee, 2)
    
    return render_template('payment.html', 
                         course=course,
                         total_price=total_price)

@app.route('/process-payment/<int:course_id>', methods=['POST'])
@require_login
def process_payment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if existing:
        flash('You are already enrolled in this course')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Get payment details from form
    payment_method = request.form.get('payment_method', 'card')
    card_number = request.form.get('card_number', '')
    cardholder_name = request.form.get('cardholder_name', '')
    
    # Simulate payment processing
    # In a real application, you would integrate with a payment processor
    # like Stripe, PayPal, etc.
    
    # For demo purposes, we'll assume all payments are successful
    payment_successful = True
    
    if payment_successful:
        # Create enrollment
        enrollment = Enrollment(user_id=session['user_id'], course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Payment successful! You are now enrolled in the course.')
        return redirect(url_for('enrollment_success', course_id=course_id))
    else:
        flash('Payment failed. Please try again.')
        return redirect(url_for('payment_page', course_id=course_id))

@app.route('/process-enrollment/<int:course_id>')
@require_login
def process_enrollment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if existing:
        flash('You are already enrolled in this course')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Create enrollment for free courses
    enrollment = Enrollment(user_id=session['user_id'], course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()
    
    flash('Successfully enrolled in course!')
    return redirect(url_for('enrollment_success', course_id=course_id))

@app.route('/enrollment-success/<int:course_id>')
@require_login
def enrollment_success(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify user is enrolled
    enrollment = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if not enrollment:
        flash('You are not enrolled in this course')
        return redirect(url_for('courses'))
    
    # Get user info
    user = User.query.get(session['user_id'])
    
    return render_template('enrollment_success.html', 
                         course=course,
                         enrollment_date=enrollment.enrolled_at,
                         user_email=user.email)

@app.route('/course/<int:course_id>')
@require_login
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if user is enrolled using relationships
    enrollment = Enrollment.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    # Get evaluations using relationships
    evaluations = course.evaluations
    
    # Get course files (only if enrolled)
    course_files = []
    if enrollment:
        course_files = course.files
    
    return render_template('course_detail.html', 
                         course=course, 
                         enrollment=enrollment, 
                         evaluations=evaluations,
                         course_files=course_files,
                         format_file_size=format_file_size)

@app.route('/evaluate/<int:course_id>', methods=['POST'])
@require_login
def evaluate_course(course_id):
    rating = int(request.form['rating'])
    comment = request.form['comment']
    
    # Check if user already evaluated this course
    existing = Evaluation.query.filter_by(
        user_id=session['user_id'], 
        course_id=course_id
    ).first()
    
    if existing:
        existing.rating = rating
        existing.comment = comment
        existing.created_at = datetime.utcnow()
    else:
        evaluation = Evaluation(
            user_id=session['user_id'],
            course_id=course_id,
            rating=rating,
            comment=comment
        )
        db.session.add(evaluation)
    
    db.session.commit()
    flash('Thank you for your evaluation!')
    return redirect(url_for('course_detail', course_id=course_id))

def get_recommendations(user_id):
    # Get courses with highest average ratings that user hasn't enrolled in
    enrolled_course_ids = db.session.query(Enrollment.course_id).filter_by(user_id=user_id).subquery()
    
    recommendations = db.session.query(
        Course,
        func.avg(Evaluation.rating).label('avg_rating'),
        func.count(Evaluation.rating).label('rating_count')
    ).outerjoin(Evaluation).filter(
        ~Course.id.in_(enrolled_course_ids)
    ).group_by(Course.id).having(
        func.count(Evaluation.rating) > 0
    ).order_by(
        func.avg(Evaluation.rating).desc(),
        func.count(Evaluation.rating).desc()
    ).limit(3).all()
    
    return recommendations

@app.route('/api/course-stats/<int:course_id>')
def course_stats(course_id):
    # Get stats using relationships and aggregations
    stats = db.session.query(
        func.count(Evaluation.id).label('total_evaluations'),
        func.avg(Evaluation.rating).label('avg_rating'),
        func.count(Enrollment.id).label('total_enrollments')
    ).select_from(Course).outerjoin(Evaluation).outerjoin(Enrollment).filter(
        Course.id == course_id
    ).first()
    
    return jsonify({
        'total_evaluations': stats.total_evaluations or 0,
        'avg_rating': round(stats.avg_rating or 0, 1),
        'total_enrollments': stats.total_enrollments or 0
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
