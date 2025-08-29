import pyodbc
import os
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, current_app
import shutil

app = Flask(__name__)
app.secret_key = 'Lepi'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'eduardflores315@gmail.com'
app.config['MAIL_PASSWORD'] = 'ifab nule rypk dbmt'
app.config['MAIL_DEFAULT_SENDER'] = 'eduardflores315@gmail.com'

mail = Mail(app)

def connect_db():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LEPILAPTOP\\SQLEXPRESS07;'
        'DATABASE=LostAndFoundSystem;'
        'Trusted_Connection=yes;'
    )
    return conn

@app.route('/')
def home():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 1 FoundID, FoundItem, Location, Description, Date, StudentID 
        FROM Found 
        ORDER BY Date DESC, FoundID DESC
    """)
    latest_found = cursor.fetchone()

    cursor.execute("""
        SELECT TOP 1 LostID, LostItem, Location, Description, Date, StudentID 
        FROM Lost 
        ORDER BY Date DESC, LostID DESC
    """)
    latest_lost = cursor.fetchone()

    conn.close()

    return render_template('pages/index.html',
                           latest_found=latest_found,
                           latest_lost=latest_lost)

@app.route('/lost')
def lost():
    item = request.args.get('item')
    location = request.args.get('location')
    return render_template('pages/lost.html', item=item, location=location)

@app.route('/found')
def found():
    item = request.args.get('item')
    location = request.args.get('location')
    return render_template('pages/found.html', item=item, location=location)

@app.route('/submit_lost', methods=['POST'])
def submit_lost():
    item = request.form['item']
    location = request.form['location']
    description = request.form['description']
    date = request.form['date']
    student_id = request.form['student_id']
    contact = request.form['contact']
    photo = request.files['photo']

    photo_filename = secure_filename(photo.filename)

    upload_folder = os.path.join('static', 'uploads', 'lost')
    photo_path = os.path.join(upload_folder, photo_filename)
    photo.save(photo_path)

    photo_relative_path = f'uploads/lost/{photo_filename}'

    conn = connect_db()
    cursor = conn.cursor()
    query = """
        INSERT INTO [Lost] (LostItem, Location, Description, Date, StudentID, Contact, Photo, Status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (
        item, location, description, date, student_id, contact, photo_relative_path, "NOT FOUND"
    ))
    conn.commit()
    conn.close()

    return redirect(url_for('recentlost'))

@app.route('/recentlost')
def recentlost():
    query = request.args.get('query', '')
    filter_by = request.args.get('filter_by', 'item')

    conn = connect_db()
    cursor = conn.cursor()

    sql = """
        SELECT LostID, LostItem, Location, Description, Date, StudentID 
        FROM Lost
    """

    if query:
        if filter_by == 'location':
            sql += " WHERE Location LIKE ?"
        elif filter_by == 'date':
            sql += " WHERE Date LIKE ?"
        else:
            sql += " WHERE LostItem LIKE ?"
        sql += " ORDER BY Date DESC, LostID DESC"
        cursor.execute(sql, ('%' + query + '%',))
    else:
        sql += " ORDER BY Date DESC, LostID DESC"
        cursor.execute(sql)

    recentfound = cursor.fetchall()
    conn.close()

    items = [{
        'id': row[0],
        'item': row[1],
        'location': row[2],
        'description': row[3],
        'date': row[4],
        'lost_by': row[5]
    } for row in recentfound]

    return render_template('pages/recentlost.html', items=items)

@app.route('/recentfound')
def recentfound():
    query = request.args.get('query', '').strip()
    filter_by = request.args.get('filter_by', 'item')

    conn = connect_db()
    cursor = conn.cursor()

    sql = """
        SELECT FoundID, FoundItem, Location, Description, Date, StudentID 
        FROM Found
    """

    if query:
        if filter_by == 'location':
            sql += " WHERE Location LIKE ?"
        elif filter_by == 'date':
            sql += " WHERE Date LIKE ?"
        else:
            sql += " WHERE FoundItem LIKE ?"
        sql += " ORDER BY Date DESC, FoundID DESC"
        cursor.execute(sql, ('%' + query + '%',))
    else:
        sql += " ORDER BY Date DESC, FoundID DESC"
        cursor.execute(sql)

    recentfound = cursor.fetchall()
    conn.close()

    items = [{
        'id': row[0],
        'item': row[1],
        'location': row[2],
        'description': row[3],
        'date': row[4],
        'found_by': row[5]
    } for row in recentfound]

    return render_template('pages/recentfound.html', items=items)

@app.route('/submit_found', methods=['POST'])
def submit_found():
    item = request.form['item']
    location = request.form['location']
    description = request.form['description']
    date = request.form['date']
    student_id = request.form['student_id']
    contact = request.form['contact']
    photo = request.files['photo']

    photo_filename = secure_filename(photo.filename)

    upload_folder = os.path.join('static', 'uploads', 'found')
    photo_path = os.path.join(upload_folder, photo_filename)
    photo.save(photo_path)

    photo_relative_path = f'uploads/found/{photo_filename}'

    conn = connect_db()
    cursor = conn.cursor()
    query = """
        INSERT INTO [Found] (FoundItem, Location, Description, Date, StudentID, Contact, Photo, Status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (
        item, location, description, date, student_id, contact, photo_relative_path, "FOUND"
    ))
    conn.commit()
    conn.close()

    return redirect(url_for('recentfound'))

@app.route('/view_lost_item/<int:lost_id>')
def view_lost_item(lost_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT LostItem, Location, Description, Date, StudentID, Contact, Photo, Status 
        FROM Lost 
        WHERE LostID = ?
    """, (lost_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        lost_item = {
            'item': item[0],
            'location': item[1],
            'description': item[2],
            'date': item[3],
            'student_id': item[4],
            'contact': item[5],
            'photo': item[6],
            'status': item[7]
        }
        return render_template('pages/view_lost_item.html', lost_item=lost_item, lost_id=lost_id)
    else:
        return "Item not found", 404
    
def send_found_notification(to_email, item_name):
    print(f"Sending email to: {to_email} about item: {item_name}")
    msg = Message(
        subject="Lost Item Found",
        recipients=[to_email],
        body=f"Good news! Your lost item '{item_name}' has been found. Please visit the Office of Student Affairs (OSA) office to claim it."
    )
    try:
        mail.send(msg)
        print("Email sent successfully")
    except Exception as e:
        print("Failed to send email:", e)

@app.route('/mark_as_found/<int:lost_id>', methods=['POST'])
def mark_as_found(lost_id):
    student_id = request.form.get('student_id')
    if not student_id:
        return "Student ID is required", 400

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT LostItem, Location, Description, Date, StudentID, Contact, Photo 
        FROM Lost 
        WHERE LostID = ?
    """, (lost_id,))
    item = cursor.fetchone()

    if item:
        print(f"Contact email from DB: {item[5]}")

        photo_path = item[6]

        old_path = os.path.join(current_app.root_path, 'static', photo_path)
        filename = os.path.basename(photo_path)
        new_relative_path = f'uploads/found/{filename}'
        new_path = os.path.join(current_app.root_path, 'static', new_relative_path)

        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        if os.path.exists(old_path):
            shutil.move(old_path, new_path)

        cursor.execute("""
            INSERT INTO Found (FoundItem, Location, Description, Date, StudentID, Contact, Photo, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item[0], item[1], item[2], item[3], student_id, item[5], new_relative_path, "FOUND"))

        cursor.execute("DELETE FROM Lost WHERE LostID = ?", (lost_id,))

        conn.commit()
        conn.close()

        send_found_notification(item[5], item[0])

        return redirect(url_for('home'))

    conn.close()
    return "Lost item not found", 404
    
@app.route('/view_found_item/<int:found_id>')
def view_found_item(found_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT FoundItem, Location, Description, Date, StudentID, Contact, Photo, Status 
        FROM Found 
        WHERE FoundID = ?
    """, (found_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        found_item = {
            'item': item[0],
            'location': item[1],
            'description': item[2],
            'date': item[3],
            'student_id': item[4],
            'contact': item[5],
            'photo': item[6],
            'status': item[7]
        }
        return render_template('pages/view_found_item.html', found_item=found_item, found_id=found_id)
    else:
        return "Item not found", 404

@app.route('/mark_as_retrieved/<int:found_id>', methods=['POST'])
def mark_as_retrieved(found_id):
    requested_by = request.form.get('requested_by')

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Photo, FoundItem, Location, Description, StudentID, Contact
        FROM Found 
        WHERE FoundID = ?
    """, (found_id,))
    result = cursor.fetchone()

    if result:
        relative_photo_path, found_item, location, description, student_id, contact = result
        photo_filename = os.path.basename(relative_photo_path)

        old_path = os.path.join(current_app.root_path, 'static', relative_photo_path)
        new_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'approval')
        os.makedirs(new_folder, exist_ok=True)
        new_path = os.path.join(new_folder, photo_filename)

        if os.path.exists(old_path):
            shutil.move(old_path, new_path)

        new_relative_path = os.path.join('uploads', 'approval', photo_filename)

        cursor.execute("""
            INSERT INTO Approval (
                FoundID, FoundItem, Location, Description, StudentID, Contact, Status, Photo, RequestedBy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            found_id, found_item, location, description, student_id, contact, 'PENDING', new_relative_path, requested_by
        ))

        cursor.execute("DELETE FROM Found WHERE FoundID = ?", (found_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)