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

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

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
        print(f"Error connecting to MySQL: {e}")
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
                INSERT IGNORE INTO admin (username, password) VALUES (%s, %s)
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
                         'Study of computer systems, programming, and software development'),
                        ('Electronics Engineering', college_ids[0][0], 40, 'ECE',
                         'Focus on electronic systems, circuits, and communication'),
                        ('Mechanical Engineering', college_ids[0][0], 50, 'MECH',
                         'Study of mechanical systems, thermodynamics, and manufacturing'),
                    ]
                    
                    cursor.executemany('''
                        INSERT INTO courses 
                        (course_name, college_id, available_seats, department, description)
                        VALUES (%s, %s, %s, %s, %s)
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
        
        # Validate input
        if not name or not email or not password or not exam_rank:
            flash('All fields are required', 'error')
            return render_template('student_register.html')
        
        if exam_rank < 1:
            flash('Exam rank must be a positive number', 'error')
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
                    INSERT INTO students (name, email, password, exam_rank)
                    VALUES (%s, %s, %s, %s)
                ''', (name, email, password, exam_rank))
                
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
            flash('All fields are required', 'error')
            return render_template('college_login.html')
        
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
                flash('Login successful!', 'success')
                return redirect(url_for('college_dashboard'))
            else:
                flash('Invalid College Name or password', 'error')
        else:
            flash('Database connection failed', 'error')
    
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
        
        connection.close()
        
        return render_template('college_dashboard.html', 
                             college=college, 
                             courses=courses, 
                             applicants=applicants,
                             total_applicants=len(applicants))
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
                flash('Admin login successful!', 'success')
                return redirect(url_for('allocator_dashboard'))
            else:
                flash('Invalid admin credentials', 'error')
        else:
            flash('Database connection failed', 'error')
    
    return render_template('allocator_login.html')

@app.route('/allocator/dashboard')
def allocator_dashboard():
    """Allocator dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('allocator_login'))
    
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

@app.route('/allocator/run_allocation', methods=['POST'])
def run_allocation():
    """Run the allocation algorithm"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('allocator_login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Simple allocation algorithm: assign students based on rank and preference
        try:
            # Clear existing allocations
            cursor.execute('DELETE FROM allotments')
            
            # Get all students ordered by rank
            cursor.execute('''
                SELECT s.student_id, s.exam_rank
                FROM students s
                ORDER BY s.exam_rank
            ''')
            students = cursor.fetchall()
            
            allocated_count = 0
            
            for student_id, rank in students:
                # Get student preferences ordered by priority
                cursor.execute('''
                    SELECT p.course_id, co.available_seats
                    FROM preferences p
                    JOIN courses co ON p.course_id = co.course_id
                    WHERE p.student_id = %s
                    ORDER BY p.priority_order
                ''', (student_id,))
                preferences = cursor.fetchall()
                
                # Try to allocate based on preferences
                for course_id, available_seats in preferences:
                    if available_seats > 0:
                        # Allocate seat
                        cursor.execute('''
                            INSERT INTO allotments (student_id, course_id, allotment_status)
                            VALUES (%s, %s, 'Allotted')
                        ''', (student_id, course_id))
                        
                        # Decrease available seats
                        cursor.execute('''
                            UPDATE courses SET available_seats = available_seats - 1
                            WHERE course_id = %s
                        ''', (course_id,))
                        
                        allocated_count += 1
                        break
            
            connection.commit()
            flash(f'Allocation completed! {allocated_count} students allocated.', 'success')
            
        except Error as e:
            flash(f'Allocation failed: {str(e)}', 'error')
            connection.rollback()
        
        connection.close()
    
    return redirect(url_for('allocator_dashboard'))

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
            WHERE s.student_id = %s AND a.allotment_status = 'Allotted'
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