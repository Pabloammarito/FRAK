from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename




app = Flask(__name__)
app.secret_key = 'hemmelig_nøgle123'

UPLOAD_FOLDER = 'static/profilbilleder'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_extra_tables():
    # Sørg for, at mappen til databasen eksisterer
    if not os.path.exists('pyxashs'):
        os.makedirs('pyxashs')

    conn = sqlite3.connect('_pyxashs_/frak.db')
    c = conn.cursor()

    # Opret Users tabel eller tilføj manglende kolonner
    c.execute('''CREATE TABLE IF NOT  EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 name TEXT,
                 size TEXT,
                 address TEXT,
                 age INTEGER,
                 is_admin INTEGER DEFAULT 0
                 )''')

    # Tjek om kolonnerne address og age findes, og tilføj dem, hvis de mangler    def init_extra_tables():
        # ...existing code...
    
        # Add phone column if it doesn't exist
    try:
            c.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    except sqlite3.OperationalError:
            pass  # Column already exists
    
        # Add confirmed_at column to vagtplan if it doesn't exist
    try:
            c.execute('ALTER TABLE vagtplan ADD COLUMN confirmed_at TIMESTAMP')
    except sqlite3.OperationalError:
            pass
    
        # Add created_at column to vagtplan if it doesn't exist
    try:
            c.execute('ALTER TABLE vagtplan ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
            pass
    
        
    try:
        c.execute('ALTER TABLE users ADD COLUMN address TEXT')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    try:
        c.execute('ALTER TABLE users ADD COLUMN age INTEGER')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    try:
        c.execute('ALTER TABLE users ADD COLUMN name TEXT')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    try:
        c.execute('ALTER TABLE users ADD COLUMN size TEXT')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    try:
        c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede
        
    # Add 'billede' column if it doesn't exist
    try:
        c.execute('ALTER TABLE users ADD COLUMN billede TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Tilføj confirmed kolonne til vagtplan hvis den ikke findes
        # Tilføj denne i din init_extra_tables()
    try:
        c.execute('ALTER TABLE vagtplan ADD COLUMN done INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    # Tilføj status kolonne til vagt_anmodninger hvis den ikke findes
    try:
        c.execute('ALTER TABLE vagt_anmodninger ADD COLUMN status INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede

    # Opret Vagtplan tabel
    c.execute('''CREATE TABLE IF NOT EXISTS vagtplan (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ansvarlig TEXT,
                 ungearbejder INTEGER,
                 date TEXT,
                 hours INTEGER,
                 confirmed INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 confirmed_at TIMESTAMP,
                 afslag_grund TEXT,
                 FOREIGN KEY (ungearbejder) REFERENCES users(id)
    )''')

    # Forsøg at tilføje afslag_grund kolonne hvis den ikke findes
    try:
        c.execute('ALTER TABLE vagtplan ADD COLUMN afslag_grund TEXT')
    except sqlite3.Error:
        # Kolonnen findes allerede, så vi fortsætter
        pass

    # Opret Opgaver tabel
    c.execute('''CREATE TABLE IF NOT EXISTS opgaver (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date TEXT NOT NULL,
                 job TEXT NOT NULL)''')

    #    # Add this to your init_extra_tables() function:
    
    c.execute('''CREATE TABLE IF NOT EXISTS dagens_arbejde (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date TEXT NOT NULL,
                 job TEXT NOT NULL,
                 person INTEGER NOT NULL,
                 vagt_id INTEGER,
                 status INTEGER DEFAULT 0,
                 message TEXT,
                 FOREIGN KEY (vagt_id) REFERENCES vagtplan(id),
                 FOREIGN KEY (person) REFERENCES users(id)
    )''')

    # Relation mellem vagtplan og brugere
    c.execute('''CREATE TABLE IF NOT EXISTS vagtplan_users (
                 vagtplan_id INTEGER,
                 user_id INTEGER,
                 FOREIGN KEY (vagtplan_id) REFERENCES vagtplan(id),
                 FOREIGN KEY (user_id) REFERENCES users(id))''')

    # Relation mellem vagtplan og gruppeleder(e)
    c.execute('''CREATE TABLE IF NOT EXISTS vagtplan_leaders (
        vagtplan_id INTEGER,
        leader_id INTEGER,
        FOREIGN KEY (vagtplan_id) REFERENCES vagtplan(id),
        FOREIGN KEY (leader_id) REFERENCES users(id))''')

    # Opret Vagtanmodninger tabel
    c.execute('''CREATE TABLE IF NOT EXISTS vagt_anmodninger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        hours INTEGER,
        status INTEGER DEFAULT 0)''')  # 0=afventer, 1=godkendt, 2=afslået

    # Opret tabel til brugerens tøjlager-valg hvis den ikke findes
    c.execute('''CREATE TABLE IF NOT EXISTS user_tojvalg (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        size TEXT,
        quantity INTEGER,
        valgt_tidspunkt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()

# Kald funktionen ved start
init_extra_tables()

# Dynamisk database-sti
DB_DIR = '_pyxashs_'
DB_PATH = os.path.join(DB_DIR, 'frak.db')

# Hjemmeside
@app.route('/')
def home():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")

# Vagtplan

@app.route('/vagtplan')
def vagtplan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Hent afventende vagter med opgaver
    c.execute('''
        SELECT v.*, da.job AS opgave
        FROM vagtplan v
        LEFT JOIN dagens_arbejde da ON v.id = da.vagt_id
        WHERE v.ungearbejder = ? AND v.confirmed = 0
    ''', (session['user_id'],))
    afventende_vagter = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

    # Hent bekræftede vagter med opgaver
    c.execute('''
        SELECT v.*, da.job AS opgave, da.status AS done
        FROM vagtplan v
        LEFT JOIN dagens_arbejde da ON v.id = da.vagt_id
        WHERE v.ungearbejder = ? AND v.confirmed = 1
    ''', (session['user_id'],))
    vagter = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

    # Hent afviste vagter med opgaver
    c.execute('''
        SELECT v.*, da.job AS opgave, v.afslag_grund
        FROM vagtplan v
        LEFT JOIN dagens_arbejde da ON v.id = da.vagt_id
        WHERE v.ungearbejder = ? AND v.confirmed = 2
    ''', (session['user_id'],))
    afviste_vagter = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

    # Hent brugerens opgaver
    c.execute('SELECT date, job FROM dagens_arbejde WHERE person = ?', (session['user_id'],))
    opgaver = [{'date': row[0], 'description': row[1]} for row in c.fetchall()]

    # Hent dagens arbejde (seneste 2 uger)
    c.execute('SELECT date, job, person FROM dagens_arbejde WHERE person = ? AND date >= DATE("now", "-14 days")', (session['user_id'],))
    dagens_arbejde = c.fetchall()

    conn.close()

    return render_template(
        'user_dashboard.html',
        afventende_vagter=afventende_vagter,
        vagter=vagter,
        afviste_vagter=afviste_vagter,
        opgaver=opgaver,
        dagens_arbejde=dagens_arbejde
    )

# Opgaver
@app.route('/stue1')
def opgaver():  
    Opgaver = [
        {"date": "5. Maj", "Jobs": "Events"},
        {"date": "9. Maj", "Jobs": "Anlæg og vedligeholdelse"},
        {"date": "14. Maj", "Jobs": "Akadamiet"},
        {"date": "22. Maj", "Jobs": "Fritidsjob med mentor"}
    ]
    return render_template("stue.html", Opgaver=Opgaver, bruger=None)

# Lager
@app.route("/stue2")
def Tøjlager():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all tøjlager items grouped by type
    Tøjlager_dict = {}
    c.execute('SELECT type, size, quantity FROM tøjlager ORDER BY type, size')
    for row in c.fetchall():
        if row[0] not in Tøjlager_dict:
            Tøjlager_dict[row[0]] = {}
        Tøjlager_dict[row[0]][row[1]] = row[2]
    
    conn.close()

    # Get selected items from session and adjust displayed quantities
    selected_sizes = session.get('selected_sizes', {})
    
    # Adjust the displayed quantities based on what's in the cart
    for item, count in selected_sizes.items():
        try:
            type, size = item.split('|')
            if type in Tøjlager_dict and size in Tøjlager_dict[type]:
                # Show the available quantity after cart items are subtracted
                Tøjlager_dict[type][size] -= count
        except (ValueError, KeyError):
            continue

    return render_template('stue.html', 
                         Tøjlager_dict=Tøjlager_dict,
                         selected_sizes=selected_sizes)
    

# Profil
@app.route('/profil')
def profil():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at se din profil.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email, fornavn, efternavn, size, address, age, billede FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    conn.close()

    if user:
        brugerdata = {
            'id': user[0],
            'email': user[1],
            'fornavn': user[2] or "",
            'efternavn': user[3] or "",
            'size': user[4],
            'address': user[5],
            'age': user[6],
            'billede': user[7]
        }
        return render_template('profil.html', bruger=brugerdata)
    else:
        flash('Bruger ikke fundet.', 'danger')
        return redirect(url_for('vagtplan'))        # ... alle dine route-funktioner ...
        
@app.route('/upload_billede', methods=['POST'])
def upload_billede():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at uploade et billede.', 'danger')
        return redirect(url_for('login'))

    if 'billede' not in request.files:
        flash('Ingen fil valgt.', 'danger')
        return redirect(url_for('profil'))

    billede = request.files['billede']
    billede.filename = secure_filename(billede.filename)

    if billede.filename == '':
        flash('Ingen fil valgt.', 'danger')
        return redirect(url_for('profil'))

    if billede:
        filename = secure_filename(billede.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        billede.save(filepath)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET billede = ? WHERE id = ?', (filepath, session['user_id']))
        conn.commit()
        conn.close()

        flash('Profilbillede opdateret!', 'success')
        return redirect(url_for('profil'))

    flash('Der opstod en fejl under upload.', 'danger')
    return redirect(url_for('profil'))
        
        
   

# Vælg størrelse
@app.route('/select_size', methods=['POST'])
def select_size():
    selected = request.form.getlist('size_selection[]')
    if not selected:
        return redirect(url_for('Tøjlager'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    selections = session.get('selected_sizes', {})

    for item in selected:
        type, size = item.split('|')
        
        # Check current inventory level
        c.execute('SELECT quantity FROM tøjlager WHERE type = ? AND size = ?', (type, size))
        result = c.fetchone()
        
        if result:
            available_quantity = result[0]
            current_selected = selections.get(item, 0)
            
            # Only add if there's stock available
            if current_selected < available_quantity:
                selections[item] = current_selected + 1

    conn.close()
    session['selected_sizes'] = selections
    return redirect(url_for('Tøjlager'))



        
    return redirect(url_for('Tøjlager'))
# Fjern valgt størrelse
@app.route('/remove_item/<item>')
def remove_item(item):
    selections = session.get('selected_sizes', {})
    if item in selections:
        selections[item] -= 1
        if selections[item] <= 0:
            del selections[item]
        session['selected_sizes'] = selections
    return redirect(url_for('Tøjlager'))


@app.route('/clear_selection')
def clear_selection():
    session.pop('selected_sizes', None)
    return redirect(url_for('Tøjlager'))  

# Indsæt confirm_selection-ruten HER
@app.route('/confirm_selection', methods=['POST'])
def confirm_selection():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    selections = session.get('selected_sizes', {})
    if not selections:
        flash('Du har ikke valgt noget tøj.', 'warning')
        return redirect(url_for('Tøjlager'))
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        for item, count in selections.items():
            type, size = item.split('|')
            # Opdater lagerbeholdningen
            c.execute('UPDATE tøjlager SET quantity = quantity - ? WHERE type = ? AND size = ?', 
                     (count, type, size))
            # Indsæt i user_tojvalg
            c.execute('INSERT INTO user_tojvalg (user_id, type, size, quantity) VALUES (?, ?, ?, ?)',
                      (session['user_id'], type, size, count))
        
        conn.commit()
        flash('Dit valg er bekræftet og registreret.', 'success')
        
        c.execute('UPDATE users SET size = ? WHERE id = ?', 
                 (', '.join(selections.keys()), session['user_id']))
        conn.commit()
        
        
        session.pop('selected_sizes', None)
        
    except sqlite3.Error as e:
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('Tøjlager'))

# Database initialisering
def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Opret users tabel hvis den ikke eksisterer
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 name TEXT,
                 size TEXT)''')
    



    # Opret clothing tabel hvis den ikke eksisterer
    c.execute('''CREATE TABLE IF NOT EXISTS clothing (
                 id INTEGER PRIMARY KEY,
                 type TEXT NOT NULL,
                 size TEXT NOT NULL,
                 quantity INTEGER NOT NULL,
                 status TEXT DEFAULT 'klar')''')  # <-- Tilføj status

    # Create tøjlager table
    c.execute('''CREATE TABLE IF NOT EXISTS tøjlager
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT NOT NULL,
                  size TEXT NOT NULL,
                  quantity INTEGER NOT NULL,
                  status TEXT DEFAULT 'klar')''')
    
    # Insert initial inventory data
    c.execute('SELECT * FROM tøjlager')
    if not c.fetchall():  # Only insert if table is empty
        # Insert T-shirts
        sizes = ['Small', 'Medium', 'Large', 'Extra Large']
        for size in sizes:
            c.execute('INSERT INTO tøjlager (type, size, quantity) VALUES (?, ?, ?)',
                     ('T-shirt', size, 20))
            
        # Insert Jakker
        for size in sizes:
            c.execute('INSERT INTO tøjlager (type, size, quantity) VALUES (?, ?, ?)',
                     ('Jakke', size, 20))
            
        # Insert Veste
        for size in sizes:
            c.execute('INSERT INTO tøjlager (type, size, quantity) VALUES (?, ?, ?)',
                     ('Vest', size, 20))
            
        # Insert Sko
        for size in range(38, 47):  # Opdateret for at inkludere størrelse 46
            c.execute('INSERT INTO tøjlager (type, size, quantity) VALUES (?, ?, ?)',
                     ('Sko', str(size), 10))
            
        # Insert Handsker
        for size in sizes:
            c.execute('INSERT INTO tøjlager (type, size, quantity) VALUES (?, ?, ?)',
                     ('Handske', size, 20))
    
    conn.commit()
    conn.close()

# Kald init ved start
init_db()

# Login-krav
@app.before_request
def require_login():
    allowed_routes = [
        'login', 'register', 'static', 'home',
        'user_dashboard',  # <-- tilføj denne linje
        'profil', 'logout'
    ]
    if request.endpoint not in allowed_routes and 'email' not in session:
        return redirect(url_for('login'))

# Lageroversigt
@app.route('/inventory')
def inventory():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT type, size, quantity FROM clothing')
    inventory = c.fetchall()
    conn.close()

    return render_template('stue.html', inventory=inventory)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fornavn = request.form['fornavn']
        efternavn = request.form['efternavn']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        age = request.form['age']
        size = request.form['size']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users 
                        (fornavn, efternavn, email, password, address, age, size, is_admin) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0)''',
                     (fornavn, efternavn, email, hashed_password, address, age, size))
            conn.commit()
            flash('Bruger oprettet! Log ind nu.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Emailen er allerede registreret!', 'danger')
        finally:
            conn.close()

    return render_template('Register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            if user and check_password_hash(user[2], password):
                session['email'] = email
                session['user_id'] = user[0]
                session['is_admin'] = user[7] if len(user) > 7 else 0
                flash("Du er nu logget ind.", "success")
                conn.close()
                # Tjek om bruger er admin
                if session['is_admin']:
                    return redirect(url_for('admin_vagtplan'))
                else:
                    return redirect(url_for('vagtplan'))
            else:
                flash("Forkert email eller adgangskode.", "danger")
        except Exception as e:
            flash("Der opstod en fejl under login.", "danger")
        finally:
            conn.close()
    return render_template('login.html')

@app.route('/rediger_profil', methods=['GET', 'POST'])
def rediger_profil():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at redigere din profil.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT fornavn, efternavn, email, address, age, size FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()

    if request.method == 'POST':
        fornavn = request.form['fornavn']
        efternavn = request.form['efternavn']
        email = request.form['email']
        address = request.form['address']
        age = request.form['age']
        size = request.form['size']
        nyt_kodeord = request.form['password']

        # Tjek om emailen allerede findes (og ikke er ens egen)
        c.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
        if c.fetchone():
            flash('Emailen er allerede i brug af en anden bruger.', 'danger')
        else:
            if nyt_kodeord:
                hashed = generate_password_hash(nyt_kodeord)
                c.execute('''UPDATE users SET fornavn=?, efternavn=?, email=?, password=?, address=?, age=?, size=? WHERE id=?''',
                          (fornavn, efternavn, email, hashed, address, age, size, session['user_id']))
            else:
                c.execute('''UPDATE users SET fornavn=?, efternavn=?, email=?, address=?, age=?, size=? WHERE id=?''',
                          (fornavn, efternavn, email, address, age, size, session['user_id']))
            conn.commit()
            flash('Profil opdateret!', 'success')
            conn.close()
            return redirect(url_for('Min_profil'))

    conn.close()
    return render_template('rediger_profil.html', user=user)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Du er nu logget ud.")
    return redirect(url_for('home'))

@app.route('/anmod_vagt', methods=['POST'])
def anmod_vagt():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at anmode om vagt.', 'danger')
        return redirect(url_for('login'))

    vagt_date = request.form.get('vagt_date')
    vagt_hours = request.form.get('vagt_hours')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vagt_anmodninger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    hours INTEGER)''')
    c.execute('INSERT INTO vagt_anmodninger (user_id, date, hours) VALUES (?, ?, ?)',
              (session['user_id'], vagt_date, vagt_hours))
    conn.commit()
    conn.close()
    flash("Vagtanmodning sendt!", "success")
    return redirect(url_for('user_dashboard'))  # <-- RET HER

@app.route('/Min_profil')
def Min_profil():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at se din profil.', 'danger')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email, fornavn, efternavn, size, address, age FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    brugerdata = {
        'id': user[0],
        'email': user[1],
        'fornavn': user[2] or "",
        'efternavn': user[3] or "",
        'size': user[4],
        'address': user[5],
        'age': user[6]
    }
    brugerdata['fulde_navn'] = (brugerdata['fornavn'] + " " + brugerdata['efternavn']).strip()
    conn.close()
    return render_template('min_profil.html', bruger=brugerdata)

@app.route('/admin/tildel', methods=['GET', 'POST'])
def tildel_vagt_opgave():
    if not session.get('is_admin'):
        flash('Kun admin kan tildele vagter og opgaver.', 'danger')
        return redirect(url_for('Min_profil'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('SELECT id, fornavn, efternavn, email FROM users WHERE is_admin=0')
        brugere = c.fetchall()

        if request.method == 'POST':
            vagt_date = request.form.get('vagt_date')
            medarbejder_id = request.form.get('medarbejder')
            entry_type = request.form.get('entry_type', 'vagt')
            opgave_type = request.form.get('opgave_type', '')
            opgave_beskrivelse = request.form.get('opgave_beskrivelse', '')
            
            # Sammensæt opgavebeskrivelse
            opgave = opgave_type
            if opgave_beskrivelse:
                opgave = f"{opgave_type}: {opgave_beskrivelse}" if opgave_type else opgave_beskrivelse

            if entry_type == 'vagt':
                vagt_hours = request.form.get('vagt_hours')
                
                # Indsæt vagt
                c.execute('''INSERT INTO vagtplan 
                           (ansvarlig, ungearbejder, date, hours, confirmed) 
                           VALUES (?, ?, ?, ?, 0)''',
                         (session['email'], medarbejder_id, vagt_date, vagt_hours))
                
                vagt_id = c.lastrowid

                # Indsæt opgave hvis den findes
                if opgave:
                    c.execute('''INSERT INTO dagens_arbejde 
                               (date, job, person, vagt_id, status) 
                               VALUES (?, ?, ?, ?, 0)''',
                             (vagt_date, opgave, medarbejder_id, vagt_id))

                flash('Vagt og opgave tildelt! Venter på bekræftelse.', 'success')
            else:
                # Indsæt kun opgave uden vagt
                c.execute('''INSERT INTO dagens_arbejde 
                           (date, job, person, status) 
                           VALUES (?, ?, ?, 0)''',
                         (vagt_date, opgave, medarbejder_id))
                
                flash('Opgave tildelt!', 'success')

            conn.commit()
            return redirect(url_for('admin_vagtplan'))

    except sqlite3.Error as e:
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
        
    finally:
        conn.close()

    return render_template('tildel.html', brugere=brugere)

@app.route('/admin/vagtplan')
def admin_vagtplan():
    if not session.get('is_admin'):
        flash('Kun admin kan se denne side.', 'danger')
        return redirect(url_for('Min_profil'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Hent afventende og afviste vagter med brugerinfo
        c.execute('''
            SELECT v.*, u.name as user_name, u.email, 
                   COALESCE(u.phone, 'Ikke angivet') as phone,
                   u.age,
                   datetime(v.created_at) as created_at,
                   datetime(v.confirmed_at) as confirmed_at
            FROM vagtplan v
            JOIN users u ON v.ungearbejder = u.id
            WHERE v.confirmed IN (0, 2)
            ORDER BY v.date
        ''')
        afventende_vagter = [dict(zip([col[0] for col in c.description], row)) 
                            for row in c.fetchall()]

        # Hent bekræftede vagter med brugerinfo
        c.execute('''
            SELECT v.*, u.name as user_name, u.email, u.phone, u.age,
                   datetime(v.created_at) as created_at,
                   datetime(v.confirmed_at) as confirmed_at
            FROM vagtplan v
            JOIN users u ON v.ungearbejder = u.id
            WHERE v.confirmed = 1
            ORDER BY v.date
        ''')
        bekraeftede_vagter = [dict(zip([col[0] for col in c.description], row)) 
                             for row in c.fetchall()]

        # Hent afviste vagter med brugerinfo
        c.execute('''
            SELECT v.*, u.name as user_name, u.email, u.phone, u.age,
                   datetime(v.created_at) as created_at,
                   datetime(v.confirmed_at) as confirmed_at,
                   v.afslag_grund
            FROM vagtplan v
            JOIN users u ON v.ungearbejder = u.id
            WHERE v.confirmed = 2
            ORDER BY v.confirmed_at DESC
        ''')
        afviste_vagter = [dict(zip([col[0] for col in c.description], row)) 
                         for row in c.fetchall()]

        # Hent vagtanmodninger med brugerinfo
        c.execute('''
            SELECT va.*, u.name as user_name, u.email, u.phone, u.age
            FROM vagt_anmodninger va
            JOIN users u ON va.user_id = u.id
            WHERE va.status = 0
            ORDER BY va.date
        ''')
        vagtanmodninger = [dict(zip([col[0] for col in c.description], row)) 
                          for row in c.fetchall()]

        # Hent dagens arbejde
        c.execute('''
            SELECT da.*, u.name 
            FROM dagens_arbejde da 
            JOIN users u ON da.person = u.id
            ORDER BY da.date DESC
        ''')
        dagens_arbejde = c.fetchall()

        # Hent medarbejderstatistik
        c.execute('''
            SELECT u.id, u.name, u.email,
                   COUNT(DISTINCT CASE WHEN v.confirmed = 1 THEN v.id END) as accepted_shifts,
                   COUNT(DISTINCT CASE WHEN da.status = 1 THEN da.id END) as completed_tasks
            FROM users u
            LEFT JOIN vagtplan v ON u.id = v.ungearbejder
            LEFT JOIN dagens_arbejde da ON u.id = da.person
            WHERE u.is_admin = 0
            GROUP BY u.id
''')
        medarbejdere = [dict(zip([col[0] for col in c.description], row)) 
                        for row in c.fetchall()]

    except sqlite3.Error as e:
        flash(f'Der opstod en databasefejl: {str(e)}', 'danger')
        return redirect(url_for('home'))

    finally:
        conn.close()

    return render_template(
        'admin_vagtplan.html',
        afventende_vagter=afventende_vagter,
        bekraeftede_vagter=bekraeftede_vagter,
        afviste_vagter=afviste_vagter,
        vagtanmodninger=vagtanmodninger,
        dagens_arbejde=dagens_arbejde,
        medarbejdere=medarbejdere
    )

@app.route('/dashboard' , methods=['GET', 'POST'])
def user_dashboard():
    if 'user_id' not in session:
        flash('Du skal være logget ind for at se dit dashboard.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Hent brugerens kommende vagter (kun bekræftede)
    c.execute('SELECT id, date, hours, confirmed FROM vagtplan WHERE ungearbejder = ?', (user_id,))
    vagter = []
    for row in c.fetchall():
        status = "Godkendt" if row[3] == 1 else ("Afvist" if row[3] == 2 else "Afventer")
        vagter.append({'id': row[0], 'date': row[1], 'hours': row[2], 'status': status})

    # Hent brugerens opgaver
    c.execute('SELECT date, job FROM dagens_arbejde WHERE person = ?', (user_id,))
    opgaver = [{'date': row[0], 'description': row[1]} for row in c.fetchall()]

    # Hent dagens arbejde (seneste 2 uger)
    c.execute('SELECT date, job, person FROM dagens_arbejde WHERE person = ? AND date >= DATE("now", "-14 days")', (user_id,))
    dagens_arbejde = [{'date': row[0], 'job': row[1], 'person': row[2]} for row in c.fetchall()]

    conn.close()

    return render_template(
        'user_dashboard.html',
        vagter=vagter,
        opgaver=opgaver,
        dagens_arbejde=dagens_arbejde
    )

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Kun admin har adgang til denne side.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

@app.route('/admin/opret_opgave', methods=['GET', 'POST'])
def opret_opgave():
    if not session.get('is_admin'):
        flash('Kun ledere kan oprette opgaver.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email FROM users WHERE is_admin=0')
    unge = c.fetchall()

    if request.method == 'POST':
        job = request.form['job']
        date = request.form['date']
        person_id = request.form['person_id']
        c.execute('INSERT INTO dagens_arbejde (date, job, person) VALUES (?, ?, ?)', (date, job, person_id))
        conn.commit()
        flash('Opgave oprettet!', 'success')
        return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('opret_opgave.html', unge=unge)

@app.route('/mine_opgaver', methods=['GET', 'POST'])
def mine_opgaver():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, date, job, person, image_path, confirmed 
                 FROM dagens_arbejde 
                 WHERE person = ?''', 
              (session['user_id'],))
    dagens_arbejde = c.fetchall()
    
    conn.close()
    
    return render_template('mine_opgaver.html', dagens_arbejde=dagens_arbejde)

@app.route('/lager/status/<int:clothing_id>/<status>')
def opdater_toj_status(clothing_id, status):
    if not session.get('is_admin'):
        flash('Kun ledere kan ændre tøj-status.', 'danger')
        return redirect(url_for('lager'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE clothing SET status=? WHERE id=?', (status, clothing_id))
    conn.commit()
    conn.close()
    flash('Tøj-status opdateret!', 'success')
    return redirect(url_for('lager'))



@app.route('/bekraeft_vagt/<int:vagt_id>', methods=['POST'])
def bekraeft_vagt(vagt_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        
        c.execute('SELECT id, date FROM vagtplan WHERE id = ? AND ungearbejder = ?', 
                 (vagt_id, session['user_id']))
        vagt = c.fetchone()
        if not vagt:
            flash('Du har ikke adgang til denne vagt.', 'danger')
            return redirect(url_for('vagtplan'))
        
        
        c.execute('''UPDATE vagtplan 
                     SET confirmed = 1, confirmed_at = CURRENT_TIMESTAMP 
                     WHERE id = ?''', 
                 (vagt_id,))
        
        # Tjek om der allerede findes en dagens_arbejde-post for denne vagt
        c.execute('SELECT id FROM dagens_arbejde WHERE vagt_id = ?', (vagt_id,))
        if not c.fetchone():
            # Hent evt. opgavebeskrivelse fra vagtplan eller brug en standardtekst
            c.execute('SELECT date, ansvarlig FROM vagtplan WHERE id = ?', (vagt_id,))
            vagtinfo = c.fetchone()
            if vagtinfo and vagtinfo[0]:
                vagt_date = vagtinfo[0]
                ansvarlig = vagtinfo[1]
                opgave = "Vagt"
                c.execute('''INSERT INTO dagens_arbejde (date, job, person, vagt_id, status) 
                             VALUES (?, ?, ?, ?, 0)''',
                          (vagt_date, opgave, session['user_id'], vagt_id))
            else:
                flash('Kunne ikke finde vagtens dato. Kontakt en administrator.', 'danger')
                conn.rollback()
                return redirect(url_for('vagtplan'))
        
        conn.commit()
        flash('Vagt bekræftet!', 'success')
        
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('vagtplan'))

@app.route('/afslaa_vagt/<int:vagt_id>', methods=['POST'])
def afslaa_vagt(vagt_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    grund = request.form.get('grund', '')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        
        c.execute('SELECT id FROM vagtplan WHERE id = ? AND ungearbejder = ?', 
                 (vagt_id, session['user_id']))
        if not c.fetchone():
            flash('Du har ikke adgang til denne vagt.', 'danger')
            return redirect(url_for('vagtplan'))
        
        
        c.execute('''UPDATE vagtplan 
                     SET confirmed = 2, afslag_grund = ?, confirmed_at = CURRENT_TIMESTAMP 
                     WHERE id = ?''', 
                 (grund, vagt_id))
        
        conn.commit()
        flash('Vagt afslået.', 'info')
        
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('vagtplan'))

@app.route('/markaer_vagt_afsluttet/<int:vagt_id>', methods=['POST'])
def markaer_vagt_afsluttet(vagt_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Opdater opgavestatus til afsluttet
        c.execute('''UPDATE dagens_arbejde 
                     SET status = 1 
                     WHERE vagt_id = ?''', 
                 (vagt_id,))
        
        conn.commit()
        flash('Vagt markeret som afsluttet!', 'success')
        
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('vagtplan'))




    
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        




@app.route('/admin/reset_vagtanmodninger', methods=['POST'])
def reset_vagtanmodninger():
    if not session.get('is_admin'):
        return redirect(url_for('admin_vagtplan'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM vagt_anmodninger')
    conn.commit()
    conn.close()
    flash('Alle vagtanmodninger er slettet.', 'success')
    return redirect(url_for('admin_vagtplan'))


@app.route('/dagens_arbejde', methods=['GET', 'POST'])
def dagens_arbejde():
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')

    conn = sqlite3.connect('_pyxashs_/frak.db')
    c = conn.cursor()

    user_id = session.get('user_id')
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    role_row = c.fetchone()
    user_role = role_row[0] if role_row else None

    if request.method == 'POST':
        if user_role not in ['gruppeleder', 'admin']:
            flash('Kun gruppeleder eller admin kan uploade til dagens arbejde.', 'danger')
            return redirect(url_for('dagens_arbejde'))
        date = request.form['date']
        job = request.form['job']
        person = request.form['person']
        image = request.files['image']

        image_path = None
        if image:
            image_path = f'static/uploads/{image.filename}'
            image.save(image_path)

        c.execute('INSERT INTO dagens_arbejde (date, job, person, image_path) VALUES (?, ?, ?, ?)', (date, job, person, image_path))
        conn.commit()
        flash ('Dagens arbejde tilføjet!', 'success')
        return redirect(url_for('dagens_arbejde'))

    # Get all users for the dropdown
    c.execute('SELECT id, name, email FROM users WHERE is_admin=0')
    brugere = c.fetchall()

    # Get all dagens arbejde entries
    c.execute('''SELECT da.*, u.name 
                 FROM dagens_arbejde da 
                 JOIN users u ON da.person = u.id
                 ORDER BY da.date DESC
''')
    dagens_arbejde = c.fetchall()

    conn.close()

    return render_template('dagens_arbejde.html', 
                         brugere=brugere, 
                         arbejde=dagens_arbejde, 
                         is_admin=user_admin)

@app.route('/admin/fjern_vagt/<int:vagt_id>')
def fjern_vagt(vagt_id):
    if not session.get('is_admin'):
        flash('Kun admin kan fjerne vagter', 'danger')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Check if vagt exists and is rejected
        c.execute('SELECT confirmed FROM vagtplan WHERE id = ?', (vagt_id,))
        vagt = c.fetchone()
        
        if vagt and vagt[0] == 2:  # Only remove if rejected
            c.execute('DELETE FROM vagtplan WHERE id = ?', (vagt_id,))
            conn.commit()
            flash('Vagt er blevet fjernet', 'success')
        else:
            flash('Vagten kunne ikke findes eller er ikke afvist', 'danger')
            
    except sqlite3.Error as e:
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
        
    finally:
        conn.close()
        
    return redirect(url_for('admin_vagtplan'))

def create_admin_user():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE email=?', ('admin@example.com',))
    if not c.fetchone():
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
        c.execute('INSERT INTO users (email, password, address, age, is_admin) VALUES (?, ?, ?, ?, ?)',
                  ('admin@example.com', hashed_password, 'Adminvej 1', 30, 1))
        conn.commit()
        print("Admin-bruger oprettet!")
    else:
        print("Admin-bruger findes allerede.")
    conn.close()

create_admin_user()

@app.route('/admin/gentildel_vagt/<int:vagt_id>')
def gentildel_vagt(vagt_id):
    if not session.get('is_admin'):
        flash('Kun admin kan udføre denne handling.', 'danger')
        return redirect(url_for('Min_profil'))
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        
        c.execute('''UPDATE vagtplan 
                     SET confirmed = 0, confirmed_at = NULL, afslag_grund = NULL 
                     WHERE id = ?''', 
                 (vagt_id,))
        
        conn.commit()
        flash('Vagt er gentildelt og afventer nu brugerens bekræftelse.', 'success')
        
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('admin_vagtplan'))

@app.route('/admin/vagtanmodning/<int:anmodning_id>/<int:status>')
def admin_vagtanmodning(anmodning_id, status):
    if not session.get('is_admin'):
        flash('Kun admin kan godkende eller afvise vagtanmodninger.', 'danger')
        return redirect(url_for('admin_vagtplan'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        
        c.execute('UPDATE vagt_anmodninger SET status = ? WHERE id = ?', (status, anmodning_id))
        conn.commit()
        if status == 1:
            flash('Vagtanmodning godkendt!', 'success')
        else:
            flash('Vagtanmodning afvist.', 'info')
    except sqlite3.Error as e:
        flash(f'Der opstod en fejl: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_vagtplan'))

@app.route('/admin/reset_vagter', methods=['POST'])
def reset_vagter():
    if not session.get('is_admin'):
        return redirect(url_for('admin_vagtplan'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE vagtplan SET confirmed=0, confirmed_at=NULL, afslag_grund=NULL')
    c.execute('UPDATE dagens_arbejde SET status=0')
    conn.commit()
    conn.close()
    flash('Alle vagter og opgaver er nulstillet til afventende.', 'success')
    return redirect(url_for('admin_vagtplan'))

@app.route('/admin/reset_afventende_vagter', methods=['POST'])
def reset_afventende_vagter():
    if not session.get('is_admin'):
        return redirect(url_for('admin_vagtplan'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('DELETE FROM vagtplan')
    conn.commit()
    conn.close()
    flash('Alle vagter er slettet.', 'success')
    return redirect(url_for('admin_vagtplan'))

@app.route('/admin/reset_dagens_arbejde', methods=['POST'])
def reset_dagens_arbejde():
    if not session.get('is_admin'):
        return redirect(url_for('admin_vagtplan'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM dagens_arbejde')
    conn.commit()
    conn.close()
    flash('Alle poster i dagens arbejde er slettet.', 'success')
    return redirect(url_for('admin_vagtplan'))

@app.route('/set_vagt_status/<int:vagt_id>/<int:status>', methods=['POST'])
def set_vagt_status(vagt_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('UPDATE dagens_arbejde SET status=? WHERE vagt_id=? AND person=?', (status, vagt_id, session['user_id']))
    conn.commit()
    conn.close() 
    return redirect(url_for('vagtplan'))
def add_name_columns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE users ADD COLUMN fornavn TEXT")
    except sqlite3.OperationalError:
        pass  # Kolonnen findes allerede
    try:
        c.execute("ALTER TABLE users ADD COLUMN efternavn TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

add_name_columns()


def update_user_names():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET fornavn = 'Ammar', efternavn = 'Mahmood' WHERE email = 'Ammar31@gmail.com'")
        c.execute("UPDATE users SET fornavn = 'Kel', efternavn = '21' WHERE email = 'Kel21@gmail.com'")
        c.execute("UPDATE users SET fornavn = 'Farah', efternavn = 'Jimale' WHERE email = 'farah.jimale11@gmail.com'")
        c.execute("UPDATE users SET fornavn = 'Yusuf', efternavn = 'Ali' WHERE email = 'Yusuf11@gmail.com'")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating user names: {e}")
    finally:
        conn.close()

update_user_names()

@app.route('/reset_lager', methods=['POST'])
def reset_lager():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for type in ['T-shirt', 'Jakke', 'Handske', 'Vest']:
        c.execute('UPDATE tøjlager SET quantity = 20 WHERE type = ?', (type,))
    
    for size in range(38, 47):
        c.execute('UPDATE tøjlager SET quantity = 10 WHERE type = ? AND size = ?', ('Sko', str(size)))
    conn.commit()
    conn.close()
    flash('Lageret er nulstillet!', 'success')
    return redirect(url_for('Tøjlager'))

@app.route('/admin/tojlager')
def admin_tojlager():
    if not session.get('is_admin'):
        flash('Kun admin har adgang til denne side.', 'danger')
        return redirect(url_for('home'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT type, size, quantity FROM tøjlager ORDER BY type, size')
    lager = c.fetchall()
    
    c.execute('''
        SELECT u.email, ut.type, ut.size, ut.quantity, ut.valgt_tidspunkt
        FROM user_tojvalg ut
        JOIN users u ON ut.user_id = u.id
        ORDER BY ut.valgt_tidspunkt DESC
    ''')
    bruger_valg = c.fetchall()
    conn.close()
    return render_template('admin_tojlager.html', lager=lager, bruger_valg=bruger_valg)

@app.route('/admin/reset_tojlager', methods=['POST'])
def admin_reset_tojlager():
    if not session.get('is_admin'):
        return redirect(url_for('admin_tojlager'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for type in ['T-shirt', 'Jakke', 'Handske', 'Vest']:
        c.execute('UPDATE tøjlager SET quantity = 20 WHERE type = ?', (type,))
    for size in range(38, 47):
        c.execute('UPDATE tøjlager SET quantity = 10 WHERE type = ? AND size = ?', ('Sko', str(size)))
    
    c.execute('DELETE FROM user_tojvalg')
    conn.commit()
    conn.close()
    flash('Lager og brugervalg er nulstillet!', 'success')
    return redirect(url_for('admin_tojlager'))

if __name__ == '__main__':
    app.run(debug=True)







