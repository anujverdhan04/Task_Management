from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import logging
from datetime import datetime, date

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Database initialization
def init_db():
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'Pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error during DB initialization: {str(e)}")

init_db()

# Helper function for database connection
def get_db_connection():
    try:
        conn = sqlite3.connect('tasks.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {str(e)}")
        return None

# Create a new task
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    
    # Validate input
    if not data or not data.get('title'):
        return jsonify({"error": "Title is required"}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    c = conn.cursor()
    
    try:
        # Add additional validation for due date
        due_date = data.get('due_date', '')
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        c.execute('''
            INSERT INTO tasks (title, description, due_date, status) 
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('title'), 
            data.get('description', ''),
            due_date,
            data.get('status', 'Pending')
        ))
        conn.commit()
        task_id = c.lastrowid
        conn.close()
        
        return jsonify({"id": task_id, "message": "Task created successfully"}), 201
    except Exception as e:
        conn.close()
        logging.error(f"Error creating task: {str(e)}")
        return jsonify({"error": "Error creating task", "details": str(e)}), 500

# View all tasks with optional overdue status
@app.route('/tasks', methods=['GET'])
def get_tasks():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    c = conn.cursor()
    status_filter = request.args.get('status')
    
    try:
        current_date = date.today()
        
        if status_filter:
            query = 'SELECT * FROM tasks WHERE status = ?'
            params = [status_filter]
            
            # Add overdue check for pending tasks
            if status_filter == 'Pending':
                query += ' AND (due_date = "" OR due_date IS NULL OR date(due_date) < ?)'
                params.append(current_date.isoformat())
        else:
            query = 'SELECT * FROM tasks'
            params = []
        
        c.execute(query, params)
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(tasks)
    except Exception as e:
        conn.close()
        logging.error(f"Error retrieving tasks: {str(e)}")
        return jsonify({"error": "Error retrieving tasks", "details": str(e)}), 500

# Update a task
@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    c = conn.cursor()
    
    try:
        # Validate due date if provided
        due_date = data.get('due_date', '')
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        c.execute('''
            UPDATE tasks 
            SET title = ?, description = ?, due_date = ?, status = ?
            WHERE id = ?
        ''', (
            data.get('title'), 
            data.get('description', ''),
            due_date,
            data.get('status', 'Pending'),
            task_id
        ))
        conn.commit()
        
        if c.rowcount == 0:
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        
        conn.close()
        return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        conn.close()
        logging.error(f"Error updating task: {str(e)}")
        return jsonify({"error": "Error updating task", "details": str(e)}), 500

# Delete a task
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    c = conn.cursor()
    
    try:
        # Check if task exists before deleting
        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        
        if not task:
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        
        conn.close()
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        conn.close()
        logging.error(f"Error deleting task: {str(e)}")
        return jsonify({"error": "Error deleting task", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
