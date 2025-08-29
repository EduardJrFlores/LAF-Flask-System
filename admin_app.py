import pyodbc
import os
import shutil
from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'Lepi'

def connect_db():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LEPILAPTOP\\SQLEXPRESS07;'
        'DATABASE=LostAndFoundSystem;'
        'Trusted_Connection=yes;'
    )
    return conn

@app.route('/')
def index():
    return redirect(url_for('login_signup'))

@app.route('/admin/login-signup')
def login_signup():
    return render_template('admin/login_signup.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Admin WHERE Username = ? OR Email = ?", (username, email))
        if cursor.fetchone():
            flash("Username or Email already exists.")
            conn.close()
            return redirect(url_for('login_signup'))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO Admin (FirstName, LastName, Email, Username, Password)
            VALUES (?, ?, ?, ?, ?)
        """, (firstname, lastname, email, username, hashed_password))
        conn.commit()
        conn.close()

        return redirect(url_for('login_signup'))

    return render_template('admin/login_signup.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Admin WHERE Username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin[5], password_input):
            print("Login successful")

            session['admin_id'] = admin[0] 
            session['admin_username'] = admin[4] 

            return redirect(url_for('dashboard'))
        else:
            print("Login failed")
            flash("Invalid username or password.")
            return redirect(url_for('login'))

    return render_template('admin/login_signup.html')

@app.route('/admin/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    cursor = conn.cursor()
    
    # Get latest lost
    cursor.execute("""
        SELECT TOP 1 LostID, LostItem, Location, Description, Date, StudentID
        FROM Lost
        ORDER BY Date DESC, LostID DESC
    """)
    latest_lost = cursor.fetchone()

    # Get latest found
    cursor.execute("""
        SELECT TOP 1 FoundID, FoundItem, Location, Description, Date, StudentID
        FROM Found
        ORDER BY Date DESC, FoundID DESC
    """)
    latest_found = cursor.fetchone()

    # Get all approvals
    cursor.execute("""
        SELECT ApprovalID, FoundItem, Description, DateSubmitted, StudentID, RequestedBy, Status
        FROM Approval
        ORDER BY DateSubmitted DESC, ApprovalID DESC
    """)
    approval_items = cursor.fetchall()

    # Get counts
    cursor.execute("SELECT COUNT(*) FROM Lost")
    lost_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Found")
    found_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Approval")
    approval_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'admin/dashboard.html',
        username=session['admin_username'],
        latest_lost=latest_lost,
        latest_found=latest_found,
        lost_count=lost_count,
        found_count=found_count,
        approval_count=approval_count,
        approval_items=approval_items  # <-- this is the list you loop through
    )

@app.route('/waitingapproval')
def waitingapproval():
    query = request.args.get('query', '').strip()
    filter_by = request.args.get('filter_by', 'item')

    conn = connect_db()
    cursor = conn.cursor()

    sql = """
        SELECT ApprovalID, FoundItem, Description, DateSubmitted, StudentID, RequestedBy 
        FROM Approval
    """

    if query:
        if filter_by == 'date':
            sql += " WHERE DateSubmitted LIKE ?"
        else:
            sql += " WHERE FoundItem LIKE ?"
        sql += " ORDER BY DateSubmitted DESC, FoundID DESC"
        cursor.execute(sql, ('%' + query + '%',))
    else:
        sql += " ORDER BY DateSubmitted DESC, FoundID DESC"
        cursor.execute(sql)

    waitingapproval = cursor.fetchall()
    conn.close()

    items = [{
        'id': row[0],
        'item': row[1],
        'description': row[2],
        'date': row[3],
        'submitted_by': row[4],
        'requested_by': row[5]
    } for row in waitingapproval]

    return render_template('admin/waitingapproval.html', items=items)

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

    return render_template('admin/recentlost.html', items=items)

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

    return render_template('admin/recentfound.html', items=items)

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
        return render_template('admin/view_lost_item.html', lost_item=lost_item, lost_id=lost_id)
    else:
        return "Item not found", 404

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
        return render_template('admin/view_found_item.html', found_item=found_item, found_id=found_id)
    else:
        return "Item not found", 404
    
@app.route('/admin/lost/edit/<int:lost_id>', methods=['GET', 'POST'])
def edit_lost_item(lost_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        item = request.form['item']
        description = request.form['description']
        date = request.form['date']

        cursor.execute("""
            UPDATE Lost
            SET LostItem = ?, Description = ?, Date = ?
            WHERE LostID = ?
        """, (item, description, date, lost_id))
        conn.commit()
        conn.close()

        return redirect(url_for('view_lost_item', lost_id=lost_id))

    # GET method - load existing data
    cursor.execute("SELECT LostID, LostItem, Location, Description, Date, StudentID FROM Lost WHERE LostID = ?", (lost_id,))
    lost_item = cursor.fetchone()
    conn.close()

    if lost_item:
        item_data = {
            'id': lost_item[0],
            'item': lost_item[1],
            'location': lost_item[2],
            'description': lost_item[3],
            'date': lost_item[4],
            'student_id': lost_item[5]
        }
        return render_template('admin/edit_lost_item.html', lost_item=item_data)
    else:
        return redirect(url_for('recentlost'))

@app.route('/admin/lost/delete/<int:lost_id>', methods=['POST'])
def delete_lost_item(lost_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT Photo FROM Lost WHERE LostID = ?", (lost_id,))
    result = cursor.fetchone()

    if result:
        relative_photo_path = result[0]

        cursor.execute("DELETE FROM Lost WHERE LostID = ?", (lost_id,))
        conn.commit()
        conn.close()

        image_path = os.path.join(current_app.root_path, 'static', relative_photo_path)
        if os.path.exists(image_path):
            os.remove(image_path)
    else:
        conn.close()

    return redirect(url_for('recentlost'))

@app.route('/admin/found/edit/<int:found_id>', methods=['GET', 'POST'])
def edit_found_item(found_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        item = request.form['item']
        description = request.form['description']
        date = request.form['date']

        cursor.execute("""
            UPDATE Found
            SET FoundItem = ?, Description = ?, Date = ?
            WHERE FoundID = ?
        """, (item, description, date, found_id))
        conn.commit()
        conn.close()

        return redirect(url_for('view_found_item', found_id=found_id))

    cursor.execute("SELECT FoundID, FoundItem, Location, Description, Date, StudentID FROM Lost WHERE LostID = ?", (found_id,))
    found_item = cursor.fetchone()
    conn.close()

    if found_item:
        item_data = {
            'id': found_item[0],
            'item': found_item[1],
            'location': found_item[2],
            'description': found_item[3],
            'date': found_item[4],
            'student_id': found_item[5]
        }
        return render_template('admin/edit_found_item.html', found_item=item_data)
    else:
        return redirect(url_for('recentfound'))

@app.route('/admin/found/delete/<int:found_id>', methods=['POST'])
def delete_found_item(found_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT Photo FROM Found WHERE FoundID = ?", (found_id,))
    result = cursor.fetchone()

    if result:
        relative_photo_path = result[0]

        cursor.execute("DELETE FROM Found WHERE FoundID = ?", (found_id,))
        conn.commit()
        conn.close()

        image_path = os.path.join(current_app.root_path, 'static', relative_photo_path)
        if os.path.exists(image_path):
            os.remove(image_path)
    else:
        conn.close()

    return redirect(url_for('recentfound'))

@app.route('/view_approval_item/<int:approval_id>')
def view_approval_item(approval_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT FoundItem, Location, Description, DateSubmitted, StudentID, Contact, Photo, Status, RequestedBy 
        FROM Approval 
        WHERE ApprovalID = ?
    """, (approval_id,))
    item = cursor.fetchone()
    conn.close()

    if item:
        approval_item = {
            'item': item[0],
            'location': item[1],
            'description': item[2],
            'date': item[3],
            'student_id': item[4],
            'contact': item[5],
            'photo': item[6].replace('\\', '/'), 
            'status': item[7],
            'requested_by': item[8]
        }
        return render_template('admin/view_approval_item.html', approval_item=approval_item, approval_id=approval_id)
    else:
        return "Item not found", 404
    
@app.route('/reject_approval_item/<int:approval_id>', methods=['POST'])
def reject_approval_item(approval_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Step 1: Get data from Approval table
    cursor.execute("""
        SELECT FoundItem, Location, Description, DateSubmitted, StudentID, Contact, Photo 
        FROM Approval 
        WHERE ApprovalID = ?
    """, (approval_id,))
    approval_data = cursor.fetchone()

    if not approval_data:
        conn.close()
        return "Approval item not found", 404

    found_item, location, description, date_submitted, student_id, contact, photo = approval_data

    # Step 2: Move image to found directory
    old_photo_path = os.path.join('static', 'uploads', 'approval', os.path.basename(photo))
    new_photo_path = os.path.join('static', 'uploads', 'found', os.path.basename(photo))

    try:
        if os.path.exists(old_photo_path):
            shutil.move(old_photo_path, new_photo_path)
        else:
            print(f"Image not found at {old_photo_path}")
    except Exception as e:
        print(f"Error moving file: {e}")
        conn.close()
        return "Image move failed", 500

    # Step 3: Insert back into Found table with updated photo path and Status = 'FOUND'
    new_photo_relpath = f"uploads/found/{os.path.basename(photo)}"
    cursor.execute("""
        INSERT INTO Found (FoundItem, Location, Description, Date, StudentID, Contact, Photo, Status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'FOUND')
    """, (found_item, location, description, date_submitted, student_id, contact, new_photo_relpath))

    # Step 4: Delete from Approval table
    cursor.execute("DELETE FROM Approval WHERE ApprovalID = ?", (approval_id,))
    conn.commit()
    conn.close()

    flash('Request rejected and item returned to Found list.', 'success')  # Optional
    return redirect(url_for('dashboard'))  # Change this to your actual route

@app.route('/approve_approval_item/<int:approval_id>', methods=['POST'])
def approve_approval_item(approval_id):
    admin_id = session.get('admin_id')  # Make sure admin ID is stored in session during login

    if not admin_id:
        return "Unauthorized", 403

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT FoundID, FoundItem, Location, Description, StudentID, Contact, DateSubmitted, Photo, RequestedBy 
        FROM Approval 
        WHERE ApprovalID = ?
    """, (approval_id,))
    data = cursor.fetchone()

    if not data:
        conn.close()
        return "Approval not found", 404

    found_id, item, location, description, student_id, contact, date_submitted, photo, requested_by = data

    old_photo_path = os.path.join('static', 'uploads', 'approval', os.path.basename(photo))
    new_photo_path = os.path.join('static', 'uploads', 'claimed', os.path.basename(photo))

    try:
        if os.path.exists(old_photo_path):
            shutil.move(old_photo_path, new_photo_path)
        else:
            print(f"Image not found at {old_photo_path}")
    except Exception as e:
        print(f"Error moving image: {e}")
        conn.close()
        return "Image move failed", 500

    new_photo_relpath = f"uploads/claimed/{os.path.basename(photo)}"

    cursor.execute("""
        INSERT INTO Claimed (ApprovalID, FoundID, FoundItem, Location, Description, StudentID, Contact, DateSubmitted, Photo, Status, RequestedBy, ID)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLAIMED', ?, ?)
    """, (approval_id, found_id, item, location, description, student_id, contact, date_submitted, new_photo_relpath, requested_by, admin_id))

    # Remove from Approval table
    cursor.execute("DELETE FROM Approval WHERE ApprovalID = ?", (approval_id,))
    conn.commit()
    conn.close()

    flash('Request approved and item marked as CLAIMED.', 'success')
    return redirect(url_for('dashboard'))  # Adjust route as needed

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(port=5001, debug=True)