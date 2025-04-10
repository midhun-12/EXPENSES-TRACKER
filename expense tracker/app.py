from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'expenses.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        income = float(request.form['income'])

        db = get_db()
        db.execute('INSERT INTO users (username, password, income) VALUES (?, ?, ?)', (username, password, income))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials!'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    expenses = db.execute('SELECT * FROM expenses WHERE user_id = ?', (session['user_id'],)).fetchall()

    total_expense = sum([expense['amount'] for expense in expenses])
    income = user['income']
    savings = income - total_expense

    # For pie chart by category
    category_totals = {}
    for expense in expenses:
        category = expense['category']
        category_totals[category] = category_totals.get(category, 0) + expense['amount']

    category_totals['Savings'] = savings if savings > 0 else 0

    return render_template('dashboard.html',
                           expenses=[dict(e) for e in expenses],
                           income=income,
                           total_expense=total_expense,
                           savings=savings,
                           category_data=json.dumps(category_totals))

@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    amount = float(request.form['amount'])
    category = request.form['category']

    db = get_db()
    db.execute('INSERT INTO expenses (user_id, title, amount, category) VALUES (?, ?, ?, ?)',
               (session['user_id'], title, amount, category))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/clear', methods=['POST'])
def clear_expenses():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    db.execute('DELETE FROM expenses WHERE user_id = ?', (session['user_id'],))
    db.commit()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with sqlite3.connect(DATABASE) as db:
        db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            income REAL NOT NULL
        )''')
        db.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
    app.run(debug=True)
