from flask import Flask, render_template, request, redirect
import mysql.connector
from config import DB_CONFIG
from datetime import datetime

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()

    # Get total books
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    # Get available books
    cursor.execute("SELECT COUNT(*) FROM books WHERE available = TRUE")
    available_books = cursor.fetchone()[0]

    # Borrowed = total - available
    borrowed_books = total_books - available_books

    conn.close()
    return render_template('index.html', total_books=total_books, available_books=available_books, borrowed_books=borrowed_books)


@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO books (title, author) VALUES (%s, %s)", (title, author))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('add_book.html')

@app.route('/borrow', methods=['GET', 'POST'])
def borrow_book():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Check if search parameter is present
    search_query = request.args.get('search', '')

    if search_query:
        # Filter books based on search query for title or author
        cursor.execute("""
            SELECT * FROM books 
            WHERE available = TRUE 
            AND (title LIKE %s OR author LIKE %s)
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        # Show all available books if no search query
        cursor.execute("SELECT * FROM books WHERE available = TRUE")
    
    books = cursor.fetchall()

    if request.method == 'POST':
        book_id = request.form['book_id']
        borrower_name = request.form['borrower_name']
        due_date = request.form['due_date']
        date_borrowed = datetime.today().strftime('%Y-%m-%d')

        cursor.execute("UPDATE books SET available = FALSE WHERE id = %s", (book_id,))
        cursor.execute("""
            INSERT INTO transactions (book_id, action, borrower_name, due_date, date_borrowed) 
            VALUES (%s, 'borrow', %s, %s, %s)
        """, (book_id, borrower_name, due_date, date_borrowed))
        conn.commit()
        conn.close()
        return redirect('/')

    conn.close()
    return render_template('borrow_book.html', books=books, current_date=datetime.today().strftime('%Y-%m-%d'))

@app.route('/return', methods=['GET', 'POST'])
def return_book():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM books WHERE available = FALSE")
    books = cursor.fetchall()

    fine = 0  # Default fine is 0
    if request.method == 'POST':
        book_id = request.form['book_id']
        cursor.execute("SELECT due_date FROM transactions WHERE book_id = %s AND action = 'borrow' ORDER BY date_borrowed DESC LIMIT 1", (book_id,))
        due_date = cursor.fetchone()

        if due_date:
            due_date = due_date['due_date']
            today = datetime.today().date()

            # Calculate fine if the book is returned late
            if today > due_date:
                days_late = (today - due_date).days
                fine = days_late * 5  # Assume 5 units per day as fine

        # Update the book as returned and available
        cursor.execute("UPDATE books SET available = TRUE WHERE id = %s", (book_id,))
        cursor.execute("INSERT INTO transactions (book_id, action) VALUES (%s, 'return')", (book_id,))
        conn.commit()

        conn.close()
        return redirect('/')

    conn.close()
    return render_template('return_book.html', books=books, fine=fine)

if __name__ == '__main__':
    app.run(debug=True)
