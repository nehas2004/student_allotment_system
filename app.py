from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
# Removed password hashing for simplicity as per user request
# from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import tempfile
import io
import csv

app = Flask(__name__)
app.secret_key = 'your_very_secret_key'  # Required for sessions to work

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'neha',
    'password': 'neha@2004',
    'database': 'student_allotment',
    'port': 3306
}

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        # Try to create the database if it doesn't exist
        try:
            temp_config = DB_CONFIG.copy()
            temp_config.pop('database', None)
            temp_connection = mysql.connector.connect(**temp_config)
            temp_cursor = temp_connection.cursor()
            temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            temp_connection.commit()
            temp_connection.close()
            print(f"Database '{DB_CONFIG['database']}' created or already exists")
            # Now try to connect again
            connection = mysql.connector.connect(**DB_CONFIG)
            return connection
        except Error as e2:
            print(f"Error creating database or connecting: {e2}")
            return None

def init_db():
    """Initialize the database with required tables and columns if they don't exist"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()

        # Create colleges table if not exists
        # Create courses table if not exists
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courses (
                    course_id INT AUTO_INCREMENT PRIMARY KEY,
                    course_name VARCHAR(100) NOT NULL,
                    college_id INT NOT NULL,
                    available_seats INT NOT NULL DEFAULT 0,
                    department VARCHAR(100) DEFAULT 'Not specified',
                    description TEXT,
                    FOREIGN KEY (college_id) REFERENCES colleges(college_id)
                )
            ''')
            print("Courses table created or already exists")
        except Error as e:
            print(f"Error creating courses table: {e}")

        # Add new columns to courses if not exists
        try:
            cursor.execute("SHOW COLUMNS FROM courses LIKE 'department'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN department VARCHAR(100)')
                print("Added department column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'description'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN description TEXT')
                print("Added description column to courses table")
        except Error as e:
            print(f"Error adding columns to courses table: {e}")

        # Create colleges table if not exists
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS colleges (
                    college_id INT AUTO_INCREMENT PRIMARY KEY,
                    college_name VARCHAR(100) NOT NULL,
                    location VARCHAR(100) NOT NULL,
                    password VARCHAR(255)
                )
            ''')
            print("Colleges table created or already exists")
        except Error as e:
            print(f"Error creating colleges table: {e}")

        # Add password column to colleges if not exists
        try:
            cursor.execute("SHOW COLUMNS FROM colleges LIKE 'password'")
            column_exists = cursor.fetchone()
            if not column_exists:
                cursor.execute('''
                    ALTER TABLE colleges ADD COLUMN password VARCHAR(255)
                ''')
                print("Added password column to colleges table")
            else:
                print("Password column already exists in colleges table")
        except Error as e:
            print(f"Error handling password column: {e}")

        # Create admin table if not exists
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin (
                    admin_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            ''')
            print("Admin table created or already exists")

            # Insert default admin if not exists
            # Store admin password as plain text (not recommended for production)
            cursor.execute('''
                INSERT INTO admin (username, password) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE password = VALUES(password)
            ''', ('admin', 'admin123'))
            print("Default admin inserted or already exists")

            # Add a sample college if none exists
            cursor.execute('SELECT COUNT(*) FROM colleges')
            if cursor.fetchone()[0] == 0:
                # Removed sample college insertion to avoid demo login values
                # cursor.execute('''
                #     INSERT INTO colleges (college_name, location, password)
                #     VALUES (%s, %s, %s)
                # ''', ('Sample College', 'Sample Location', 'college123'))
                # print("Sample college added")
                pass

        except Error as e:
            print(f"Error creating admin table: {e}")

        # Create allotments table if not exists
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS allotments (
                    allotment_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    course_id INT NOT NULL,
                    allotment_status VARCHAR(50) DEFAULT 'Allocated',
                    allotment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    FOREIGN KEY (course_id) REFERENCES courses(course_id),
                    UNIQUE KEY unique_allotment (student_id)
                )
            ''')
            print("Allotments table created or already exists")
        except Error as e:
            print(f"Error creating allotments table: {e}")

        # Add allotment_date column to allotments table if not exists
        try:
            cursor.execute("SHOW COLUMNS FROM allotments LIKE 'allotment_date'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE allotments ADD COLUMN allotment_date DATETIME DEFAULT CURRENT_TIMESTAMP')
                print("Added allotment_date column to allotments table")
        except Error as e:
            print(f"Error adding allotment_date column to allotments table: {e}")

        # Add category-specific seat columns to courses if not exists
        try:
            cursor.execute("SHOW COLUMNS FROM courses LIKE 'gen_seats'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN gen_seats INT DEFAULT 0')
                print("Added gen_seats column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'obc_seats'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN obc_seats INT DEFAULT 0')
                print("Added obc_seats column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'sc_seats'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN sc_seats INT DEFAULT 0')
                print("Added sc_seats column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'st_seats'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN st_seats INT DEFAULT 0')
                print("Added st_seats column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'ews_seats'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN ews_seats INT DEFAULT 0')
                print("Added ews_seats column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'gen_filled'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN gen_filled INT DEFAULT 0')
                print("Added gen_filled column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'obc_filled'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN obc_filled INT DEFAULT 0')
                print("Added obc_filled column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'sc_filled'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN sc_filled INT DEFAULT 0')
                print("Added sc_filled column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'st_filled'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN st_filled INT DEFAULT 0')
                print("Added st_filled column to courses table")

            cursor.execute("SHOW COLUMNS FROM courses LIKE 'ews_filled'")
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE courses ADD COLUMN ews_filled INT DEFAULT 0')
                print("Added ews_filled column to courses table")
        except Error as e:
            print(f"Error adding category columns to courses table: {e}")

        # Add sample courses if none exist
        try:
            cursor.execute('SELECT COUNT(*) FROM courses')
            course_count = cursor.fetchone()[0]

            if course_count == 0:
                # First get college IDs
                cursor.execute('SELECT college_id FROM colleges')
                college_ids = cursor.fetchall()

                if college_ids:
                    sample_courses = [
                        ('Computer Science Engineering', college_ids[0][0], 60, 'CSE',
                         'Study of computer systems, programming, and software development',
                         24, 16, 9, 5, 6),  # GEN:40%, OBC:27%, SC:15%, ST:7.5%, EWS:10%
                        ('Electronics Engineering', college_ids[0][0], 40, 'ECE',
                         'Focus on electronic systems, circuits, and communication',
                         16, 11, 6, 3, 4),
                        ('Mechanical Engineering', college_ids[0][0], 50, 'MECH',
                         'Study of mechanical systems, thermodynamics, and manufacturing',
                         20, 14, 8, 4, 5),
                    ]

                    cursor.executemany('''
                        INSERT INTO courses
                        (course_name, college_id, available_seats, department, description,
                         gen_seats, obc_seats, sc_seats, st_seats, ews_seats)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', sample_courses)
                    print("Sample courses added")
        except Error as e:
            print(f"Error adding sample courses: {e}")

        connection.commit()
        connection.close()

@app.route('/')
def index():
    """Main role selection screen"""
    return render_template('index.html')

# Student routes
@app.route('/student')
def student_portal():
    """Student portal - redirect to login if not logged in, dashboard if logged in"""
    if 'student_id' in session:
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('student_login'))

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    """Student registration"""
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        exam_rank = int(request.form['exam_rank'])
        category = request.form['category'].strip()

        # Validate input
        if not name or not email or not password or not exam_rank or not category:
            flash('All fields are required', 'error')
            return render_template('student_register.html')

        if exam_rank < 1:
            flash('Exam rank must be a positive number', 'error')
            return render_template('student_register.html')

        if category not in ['GEN', 'OBC', 'SC', 'ST', 'EWS']:
            flash('Invalid category selected', 'error')
            return render_template('student_register.html')

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Check if student already exists
            cursor.execute('SELECT student_id FROM students WHERE email = %s OR exam_rank = %s',
                         (email, exam_rank))
            existing = cursor.fetchone()

            if existing:
                flash('A student with this email or exam rank already exists', 'error')
                connection.close()
                return render_template('student_register.html')

            # Insert new student
            try:
                # Store password as plain text (not recommended for production)
                cursor.execute('''
                    INSERT INTO students (name, email, password, exam_rank, category)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (name, email, password, exam_rank, category))

                connection.commit()
                flash('Registration successful! Please login.', 'success')
                connection.close()
                return redirect(url_for('student_login'))

            except Error as e:
                flash(f'Registration failed: {str(e)}', 'error')
                connection.close()
        else:
            flash('Database connection failed', 'error')

    return render_template('student_register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    """Student login"""
    # Clear any existing flash messages when showing login form
    if request.method == 'GET':
        session.pop('_flashes', None)
        return render_template('student_login.html')
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('All fields are required', 'error')
            return render_template('student_login.html')
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute('SELECT student_id, name, password FROM students WHERE email = %s', (email,))
                student = cursor.fetchone()
                
                if student and student['password'] == password:
                    # Login successful
                    session['student_id'] = student['student_id']
                    session['student_name'] = student['name']
                    flash('Login successful!', 'success')
                    return redirect(url_for('student_dashboard'))
                else:
                    flash('Invalid email or password', 'error')
            except Error as e:
                flash(f'Database error: {str(e)}', 'error')
            finally:
                connection.close()
        else:
            flash('Database connection failed', 'error')
        
        return render_template('student_login.html')
    
    return render_template('student_login.html')

@app.route('/student/dashboard')
def student_dashboard():
    """Student dashboard"""
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    
    student_id = session['student_id']
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Get student info
        cursor.execute('SELECT name, email, exam_rank FROM students WHERE student_id = %s', (student_id,))
        student = cursor.fetchone()
        
        # Get student's preferences with course and college details
        cursor.execute('''
            SELECT c.college_name, co.course_name, p.priority_order 
            FROM preferences p
            JOIN courses co ON p.course_id = co.course_id
            JOIN colleges c ON co.college_id = c.college_id
            WHERE p.student_id = %s
            ORDER BY p.priority_order
        ''', (student_id,))
        preferences = cursor.fetchall()
        
        # Check if student has been allocated
        cursor.execute('''
            SELECT c.college_name, co.course_name, a.allotment_status
            FROM allotments a
            JOIN courses co ON a.course_id = co.course_id
            JOIN colleges c ON co.college_id = c.college_id
            WHERE a.student_id = %s
        ''', (student_id,))
        allocation = cursor.fetchone()
        
        # Get available courses for preference selection with all details
        cursor.execute('''
            SELECT co.course_id, co.course_name, c.college_name, co.available_seats,
                   c.location,
                   COALESCE(co.department, 'Not specified') as department,
                   COALESCE(co.description, 'No description available') as description
            FROM courses co
            JOIN colleges c ON co.college_id = c.college_id
            WHERE co.available_seats > 0
            ORDER BY c.college_name, co.course_name
        ''', )
        available_courses = cursor.fetchall()
        
        connection.close()
        
        return render_template('student_dashboard.html', 
                             student=student, 
                             preferences=preferences, 
                             allocation=allocation,
                             available_courses=available_courses)
    else:
        flash('Database connection failed', 'error')
        return redirect(url_for('student_login'))

@app.route('/student/add_preference', methods=['POST'])
def add_preference():
    """Add or update student preferences"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    student_id = session['student_id']
    data = request.get_json()
    
    if not data or 'preferences' not in data:
        return jsonify({'success': False, 'message': 'No preferences provided'}), 400
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Check if student already submitted preferences
        cursor.execute('SELECT COUNT(*) FROM preferences WHERE student_id = %s', (student_id,))
        has_preferences = cursor.fetchone()[0] > 0
        
        # Check if student has been allocated
        cursor.execute('SELECT COUNT(*) FROM allotments WHERE student_id = %s', (student_id,))
        is_allocated = cursor.fetchone()[0] > 0
        
        if has_preferences:
            return jsonify({
                'success': False, 
                'message': 'You have already submitted your preferences. They cannot be modified.'
            }), 400
            
        if is_allocated:
            return jsonify({
                'success': False, 
                'message': 'You have already been allocated. Preferences cannot be modified.'
            }), 400
        
        connection.close()
        
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        try:
            # Clear existing preferences
            cursor.execute('DELETE FROM preferences WHERE student_id = %s', (student_id,))
            
            # Add new preferences
            for pref in data['preferences']:
                cursor.execute('''
                    INSERT INTO preferences (student_id, course_id, priority_order)
                    VALUES (%s, %s, %s)
                ''', (student_id, pref['courseId'], pref['priority']))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Preferences saved successfully!'})
            
        except Error as e:
            connection.rollback()
            return jsonify({'success': False, 'message': f'Error saving preferences: {str(e)}'}), 500
        finally:
            connection.close()
    
    return jsonify({'success': False, 'message': 'Database connection failed'}), 500

@app.route('/student/logout')
def student_logout():
    """Student logout"""
    session.pop('student_id', None)
    session.pop('student_name', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# College routes
@app.route('/college')
def college_portal():
    """College portal - redirect to login if not logged in, dashboard if logged in"""
    if 'college_id' in session:
        return redirect(url_for('college_dashboard'))
    return redirect(url_for('college_login'))

@app.route('/college/register', methods=['GET', 'POST'])
def college_register():
    """College registration"""
    if request.method == 'POST':
        college_name = request.form['college_name'].strip()
        location = request.form['location'].strip()
        password = request.form['password']
        
        # Validate input
        if not college_name or not location or not password:
            flash('All fields are required', 'error')
            return render_template('college_register.html')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            
            # Check if college already exists
            cursor.execute('SELECT college_id FROM colleges WHERE college_name = %s AND location = %s', 
                         (college_name, location))
            existing = cursor.fetchone()
            
            if existing:
                flash('A college with this name and location already exists', 'error')
                connection.close()
                return render_template('college_register.html')
            
            # Insert new college
            try:
                # Store password as plain text (not recommended for production)
                cursor.execute('''
                    INSERT INTO colleges (college_name, location, password)
                    VALUES (%s, %s, %s)
                ''', (college_name, location, password))

                connection.commit()
                college_id = cursor.lastrowid

                flash(f'Registration successful! Your College ID is: {college_id}', 'success')
                connection.close()
                return redirect(url_for('college_login'))
                
            except Error as e:
                flash(f'Registration failed: {str(e)}', 'error')
                connection.close()
        else:
            flash('Database connection failed', 'error')
    
    return render_template('college_register.html')

@app.route('/college/login', methods=['GET', 'POST'])
def college_login():
    """College login"""
    if request.method == 'POST':
        college_name = request.form['college_name'].strip()
        password = request.form['password']
        
        if not college_name or not password:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute('SELECT college_id, college_name, password FROM colleges WHERE college_name = %s',
                         (college_name,))
            college = cursor.fetchone()
            connection.close()

            if college and college[2] == password:
                session['college_id'] = college[0]
                session['college_name'] = college[1]
                return jsonify({'success': True, 'message': 'Login successful'})
            else:
                return jsonify({'success': False, 'message': 'Invalid College Name or password'}), 401
        else:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    return render_template('college_login.html')

@app.route('/college/dashboard')
def college_dashboard():
    """College dashboard"""
    if 'college_id' not in session:
        return redirect(url_for('college_login'))
    
    college_id = session['college_id']
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Get college info: college_name, location, college_id (as code)
        cursor.execute('SELECT college_name, location, college_id FROM colleges WHERE college_id = %s', 
                     (college_id,))
        college_info = cursor.fetchone()
        
        # Get total seats as sum of available seats from courses
        cursor.execute('SELECT COALESCE(SUM(available_seats), 0) FROM courses WHERE college_id = %s', (college_id,))
        total_seats = cursor.fetchone()[0]
        
        # Compose college tuple as expected by template
        college = (college_info[0], college_info[1], college_info[2], total_seats)
        
        # Get courses offered by this college
        cursor.execute('SELECT course_id, course_name, available_seats FROM courses WHERE college_id = %s', 
                     (college_id,))
        courses = cursor.fetchall()
        
        # Get students who applied for courses in this college
        cursor.execute('''
            SELECT DISTINCT s.name, s.email, s.exam_rank
            FROM preferences p
            JOIN courses co ON p.course_id = co.course_id
            JOIN students s ON p.student_id = s.student_id
            WHERE co.college_id = %s
            ORDER BY s.exam_rank
        ''', (college_id,))
        applicants = cursor.fetchall()

        # Get allocated students for this college
        cursor.execute('''
            SELECT s.name, s.exam_rank, s.category, 1 as allotment_round, a.allotment_date
            FROM allotments a
            JOIN students s ON a.student_id = s.student_id
            JOIN courses co ON a.course_id = co.course_id
            WHERE co.college_id = %s AND a.allotment_status = 'Allocated'
            ORDER BY a.allotment_date DESC
        ''', (college_id,))
        allocated_students = cursor.fetchall()

        connection.close()

        return render_template('college_dashboard.html',
                             college=college,
                             courses=courses,
                             applicants=applicants,
                             total_applicants=len(applicants),
                             allocated_students=allocated_students)
    else:
        flash('Database connection failed', 'error')
        return redirect(url_for('college_login'))

@app.route('/college/add_course', methods=['POST'])
def add_course():
    """Add a new course"""
    if 'college_id' not in session:
        return redirect(url_for('college_login'))
    
    college_id = session['college_id']
    course_name = request.form['course_name'].strip()
    available_seats = int(request.form['available_seats'])
    
    if not course_name or available_seats < 1:
        flash('Please provide valid course details', 'error')
        return redirect(url_for('college_dashboard'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO courses (course_name, available_seats, college_id) 
                VALUES (%s, %s, %s)
            ''', (course_name, available_seats, college_id))
            
            connection.commit()
            flash('Course added successfully!', 'success')
        except Error as e:
            flash(f'Error adding course: {str(e)}', 'error')
        
        connection.close()
    
    return redirect(url_for('college_dashboard'))

@app.route('/college/logout')
def college_logout():
    """College logout"""
    session.pop('college_id', None)
    session.pop('college_name', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# Allocator routes (Admin)
@app.route('/allocator')
def allocator_portal():
    """Allocator portal - admin dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('allocator_login'))
    return redirect(url_for('allocator_dashboard'))

@app.route('/allocator/login', methods=['GET', 'POST'])
def allocator_login():
    """Allocator login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute('SELECT password FROM admin WHERE username = %s', (username,))
            admin = cursor.fetchone()
            connection.close()

            if admin and admin[0] == password:
                session['admin_logged_in'] = True
                session['admin_username'] = username
                session.modified = True
                session.permanent = True
                return jsonify({'success': True, 'message': 'Admin login successful'})
            else:
                return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401
        else:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    return render_template('allocator_login.html')

@app.route('/allocator/dashboard')
def allocator_dashboard():
    """Allocator dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('allocator_login'))

    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Get system statistics
            cursor.execute('SELECT COUNT(*) FROM students')
            total_students = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM colleges')
            total_colleges = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM courses')
            total_courses = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM allotments')
            total_allocations = cursor.fetchone()[0]

            # Get all students with their preferences
            cursor.execute('''
                SELECT s.student_id, s.name, s.email, s.exam_rank,
                       GROUP_CONCAT(CONCAT(co.course_name, ' (', c.college_name, ')') ORDER BY p.priority_order) as preferences
                FROM students s
                LEFT JOIN preferences p ON s.student_id = p.student_id
                LEFT JOIN courses co ON p.course_id = co.course_id
                LEFT JOIN colleges c ON co.college_id = c.college_id
                GROUP BY s.student_id, s.name, s.email, s.exam_rank
                ORDER BY s.exam_rank
            ''')
            students_with_preferences = cursor.fetchall()

            connection.close()

            return render_template('allocator_dashboard.html',
                                 total_students=total_students,
                                 total_colleges=total_colleges,
                                 total_courses=total_courses,
                                 total_allocations=total_allocations,
                                 students_with_preferences=students_with_preferences)
        else:
            flash('Database connection failed', 'error')
            return redirect(url_for('allocator_login'))
    except Error as e:
        print(f"Database error in allocator dashboard: {e}")
        flash('Database error occurred', 'error')
        return redirect(url_for('allocator_login'))
@app.route('/allocator/allocate', methods=['POST'])
def allocator_allocate():
    """Run category-based allocation algorithm with specified number of students"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401
    
    num_to_allocate = int(request.form.get('num_to_allocate', 0))
    
    if num_to_allocate < 1:
        return jsonify({'success': False, 'error': 'Invalid number of students'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Step 1: Reset filled counts for all courses
        cursor.execute('''
            UPDATE courses 
            SET gen_filled = 0, obc_filled = 0, sc_filled = 0, st_filled = 0, ews_filled = 0
        ''')
        
        # Step 2: Clear existing allocations
        cursor.execute('DELETE FROM allotments')
        
        # Step 3: Get students ordered by exam_rank, limit to num_to_allocate
        cursor.execute('''
            SELECT student_id, name, exam_rank, category
            FROM students
            ORDER BY exam_rank
            LIMIT %s
        ''', (num_to_allocate,))
        students = cursor.fetchall()
        
        allocated_count = 0
        allocation_details = []
        
        # Step 4: Process each student
        for student in students:
            student_id = student['student_id']
            student_category = student['category']
            
            # Get student preferences ordered by priority
            cursor.execute('''
                SELECT p.course_id, c.course_name, c.college_id, col.college_name,
                       c.gen_seats, c.obc_seats, c.sc_seats, c.st_seats, c.ews_seats,
                       c.gen_filled, c.obc_filled, c.sc_filled, c.st_filled, c.ews_filled
                FROM preferences p
                JOIN courses c ON p.course_id = c.course_id
                JOIN colleges col ON c.college_id = col.college_id
                WHERE p.student_id = %s
                ORDER BY p.priority_order
            ''', (student_id,))
            preferences = cursor.fetchall()
            
            allocated = False
            
            # Step 5: Try to allocate based on preferences
            for pref in preferences:
                course_id = pref['course_id']
                
                # Check if category has available seats
                category_seats_col = f'{student_category.lower()}_seats'
                category_filled_col = f'{student_category.lower()}_filled'
                
                category_seats = pref[category_seats_col]
                category_filled = pref[category_filled_col]
                
                if category_filled < category_seats:
                    # Allocate seat
                    cursor.execute('''
                        INSERT INTO allotments (student_id, course_id, allotment_status, allotment_date)
                        VALUES (%s, %s, 'Allocated', NOW())
                    ''', (student_id, course_id))
                    
                    # Increment filled count for this category
                    cursor.execute(f'''
                        UPDATE courses 
                        SET {category_filled_col} = {category_filled_col} + 1
                        WHERE course_id = %s
                    ''', (course_id,))
                    
                    allocated_count += 1
                    allocation_details.append({
                        'student_id': student_id,
                        'name': student['name'],
                        'rank': student['exam_rank'],
                        'category': student_category,
                        'course': pref['course_name'],
                        'college': pref['college_name']
                    })
                    allocated = True
                    break
            
            # If not allocated, student remains unallocated
            if not allocated:
                allocation_details.append({
                    'student_id': student_id,
                    'name': student['name'],
                    'rank': student['exam_rank'],
                    'category': student_category,
                    'status': 'Not Allocated - No seats available in preferences'
                })
        
        connection.commit()
        
        return jsonify({
            'success': True,
            'allocated_count': allocated_count,
            'total_processed': len(students),
            'details': allocation_details
        })
        
    except Error as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        connection.close()


@app.route('/allocator/allocations')
def get_allocations():
    """Get all current allocations with student and course details"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify([])
    
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT 
            a.allotment_id,
            s.student_id,
            s.name as student_name,
            s.exam_rank,
            s.category,
            c.course_name,
            col.college_name,
            a.allotment_status,
            a.allotment_date
        FROM allotments a
        JOIN students s ON a.student_id = s.student_id
        JOIN courses c ON a.course_id = c.course_id
        JOIN colleges col ON c.college_id = col.college_id
        ORDER BY s.exam_rank
    ''')
    
    allocations = cursor.fetchall()
    connection.close()
    
    # Convert datetime to string
    for alloc in allocations:
        if alloc.get('allotment_date'):
            alloc['allotment_date'] = alloc['allotment_date'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(allocations)


@app.route('/allocator/delete/<int:allotment_id>', methods=['POST'])
def delete_allocation(allotment_id):
    """Delete a specific allocation"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get allocation details before deleting
        cursor.execute('''
            SELECT a.student_id, a.course_id, s.category
            FROM allotments a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.allotment_id = %s
        ''', (allotment_id,))
        
        alloc = cursor.fetchone()
        
        if not alloc:
            return jsonify({'success': False, 'error': 'Allocation not found'}), 404
        
        # Delete the allocation
        cursor.execute('DELETE FROM allotments WHERE allotment_id = %s', (allotment_id,))
        
        # Decrement the category filled count
        category = alloc['category'].lower()
        cursor.execute(f'''
            UPDATE courses 
            SET {category}_filled = {category}_filled - 1
            WHERE course_id = %s AND {category}_filled > 0
        ''', (alloc['course_id'],))
        
        connection.commit()
        
        return jsonify({'success': True, 'message': 'Allocation deleted successfully'})
        
    except Error as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        connection.close()


@app.route('/allocator/download')
def download_allocations_csv():
    """Download allocations as CSV"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('allocator_login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed', 'error')
        return redirect(url_for('allocator_dashboard'))
    
    cursor = connection.cursor()
    
    cursor.execute('''
        SELECT 
            a.allotment_id,
            s.student_id,
            s.name as student_name,
            s.exam_rank,
            s.category,
            c.course_name,
            col.college_name,
            a.allotment_status,
            a.allotment_date
        FROM allotments a
        JOIN students s ON a.student_id = s.student_id
        JOIN courses c ON a.course_id = c.course_id
        JOIN colleges col ON c.college_id = col.college_id
        ORDER BY s.exam_rank
    ''')
    
    allocations = cursor.fetchall()
    connection.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Allotment ID', 'Student ID', 'Student Name', 'Exam Rank', 'Category', 
                     'Course Name', 'College Name', 'Status', 'Allotment Date'])
    
    # Write data
    for alloc in allocations:
        writer.writerow(alloc)
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'allocations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/allocator/logout')
def allocator_logout():
    """Allocator logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully', 'info')
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    return "Internal Server Error", 500

@app.route('/student/download_memo')
def download_allotment_memo():
    """Generate and download allotment memo as PDF"""
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    
    student_id = session['student_id']
    connection = get_db_connection()
    
    if connection:
        cursor = connection.cursor()
        
        # Get student and allotment details
        cursor.execute('''
            SELECT s.name, s.email, s.exam_rank,
                   c.college_name, c.location,
                   co.course_name, a.allotment_date
            FROM students s
            JOIN allotments a ON s.student_id = a.student_id
            JOIN courses co ON a.course_id = co.course_id
            JOIN colleges c ON co.college_id = c.college_id
            WHERE s.student_id = %s AND a.allotment_status = 'Allocated'
        ''', (student_id,))
        
        result = cursor.fetchone()
        connection.close()
        
        if not result:
            flash('No allotment found', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Create PDF
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        doc = SimpleDocTemplate(temp_pdf.name, pagesize=letter)
        
        # Build PDF content
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        elements.append(Paragraph('ALLOTMENT MEMO', title_style))
        elements.append(Spacer(1, 20))
        
        # Student details
        data = [
            ['Student Name:', result[0]],
            ['Email:', result[1]],
            ['Exam Rank:', str(result[2])],
            ['Allotted College:', result[3]],
            ['College Location:', result[4]],
            ['Allotted Course:', result[5]],
            ['Allotment Date:', result[6].strftime('%Y-%m-%d') if result[6] else 'N/A']
        ]
        
        # Create table
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Footer
        footer_text = '''
        This is an official allotment memo. Please keep this document safe.
        Present this memo at the college during admission.
        '''
        elements.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        temp_pdf.close()
        
        return send_file(
            temp_pdf.name,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'allotment_memo_{student_id}.pdf'
        )
    
    flash('Could not generate allotment memo', 'error')
    return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    # Initialize database connection
    init_db()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)