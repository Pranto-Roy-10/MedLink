from flask import Flask, render_template, redirect, url_for, request, flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'medlife-secure-key-placeholder'

# ─────────────────────────────────────────────
# Context Processor – inject globals into all templates
# ─────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now().year,
        'app_name': 'MedLife',
    }

# ─────────────────────────────────────────────
# Public Pages
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('public/landing.html')

@app.route('/about')
def about():
    return render_template('public/about.html')

@app.route('/features')
def features():
    return render_template('public/features.html')

@app.route('/contact')
def contact():
    return render_template('public/contact.html')

# ─────────────────────────────────────────────
# Auth Pages
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        flash('Demo mode: authentication not yet implemented.', 'info')
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        flash('Demo mode: registration not yet implemented.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('auth/two_factor.html')

# ─────────────────────────────────────────────
# App Dashboards
# ─────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    return render_template('app/dashboard.html', role='doctor')

@app.route('/dashboard/doctor')
def doctor_dashboard():
    return render_template('app/doctor_dashboard.html', role='doctor')

@app.route('/dashboard/specialist')
def specialist_dashboard():
    return render_template('app/specialist_dashboard.html', role='specialist')

@app.route('/dashboard/patient')
def patient_dashboard():
    return render_template('app/patient_dashboard.html', role='patient')

@app.route('/dashboard/admin')
def admin_dashboard():
    return render_template('app/admin_dashboard.html', role='admin')

# ─────────────────────────────────────────────
# Feature Pages
# ─────────────────────────────────────────────
@app.route('/referrals/create')
def create_referral():
    return render_template('features/create_referral.html', role='doctor')

@app.route('/referrals/sent')
def sent_referrals():
    return render_template('features/sent_referrals.html', role='doctor')

@app.route('/referrals/received')
def received_referrals():
    return render_template('features/received_referrals.html', role='specialist')

@app.route('/referrals/<int:ref_id>')
def referral_details(ref_id):
    return render_template('features/referral_details.html', ref_id=ref_id, role='doctor')

@app.route('/chat')
def secure_chat():
    return render_template('features/secure_chat.html', role='doctor')

@app.route('/prescriptions')
def prescriptions():
    return render_template('features/prescriptions.html', role='doctor')

@app.route('/profile')
def profile():
    return render_template('features/profile.html', role='doctor')

@app.route('/keys')
def key_management():
    return render_template('features/key_management.html', role='doctor')

@app.route('/audit-logs')
def audit_logs():
    return render_template('features/audit_logs.html', role='admin')

@app.route('/notifications')
def notifications():
    return render_template('features/notifications.html', role='doctor')

@app.route('/settings')
def settings():
    return render_template('features/settings.html', role='doctor')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
