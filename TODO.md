# TODO List for Backend and Database Setup

## 1. Database Tables
- [x] Tables already created in MySQL (students, courses, preferences, allotments, colleges, admin)

## 2. Review Backend Code
- [x] Checked for syntax errors: No syntax errors found
- [x] Verified database connection handling: Connections are opened/closed properly in each route
- [x] Ensured routes are defined and secured: Sessions used for authentication, routes check session keys
- [x] Potential improvements: Add more logging for debugging, use connection pool for production

## 3. Test Database Connection
- [x] Ran the app successfully: Flask app started on http://127.0.0.1:5000
- [x] Confirmed backend interacts with database: Tables created/checked, default admin inserted

## 4. College Registration and Login
- [x] Fixed college registration to store plain text passwords and connect to colleges table
- [x] Removed demo login values (sample college insertion and hardcoded credentials)
- [x] Ensured login takes values from colleges table and navigates to dashboard on success

## 5. Optional: Add Seed Data
- [ ] Add sample data for testing if needed (not required for basic functionality)
