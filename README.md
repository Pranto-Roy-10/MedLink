# MedLink - Secure Medical Collaboration Platform

A professional, enterprise-grade Flask-based medical platform for secure referrals and patient-doctor collaboration. Built with modern design principles and advanced cryptography, featuring multi-level security, real-time messaging, and comprehensive role-based access control.

## ✨ Core Features Implemented

### 🔐 **Advanced Cryptography & Security**
- **RSA Encryption**: 1024-bit RSA key generation, encryption/decryption for email and sensitive data
- **Elliptic Curve Cryptography (ECC)**: SECP256K1 curve implementation for secure key exchange
- **SHA-256 Hashing**: Cryptographic hashing for password storage and data integrity
- **HMAC Authentication**: Message authentication codes for data integrity verification
- **Digital Signatures**: RSA-based signatures for authentication and non-repudiation
- **Two-Factor Authentication (2FA)**: Challenge-response using cryptographic signatures
- **End-to-End Message Encryption**: ECC-based encryption for real-time chat messages
- **Steganographic Prescription Storage**: Hidden data storage in prescription documents


### 📊 **Dashboard & User Features**
- **Role-Based Portals**: Separate interfaces for Patients, Doctors, and Specialists
- **Real-Time Chat**: SocketIO-based messaging with end-to-end encryption
- **Message Encryption**: All chat messages encrypted using ECC SECP256K1
- **Prescription Management**: Secure document storage with steganography
- **Medical Referrals**: Doctor to Specialist referral system with encryption
- **User Profile Management**: Editable profiles with secure password hashing
- **Activity Logging**: Complete audit trail of user actions

### 🛡️ **Admin Features**
- **Admin Dashboard**: System monitoring and user management
- **Encryption Demo**: Live demonstrations of RSA and ECC algorithms
- **Key Rotation**: Cryptographic key management interface
- **System Log Viewer**: Real-time system activity monitoring
- **Attack Simulation**: Educational tool demonstrating security vulnerabilities

### 📱 **Responsive Design**
- Clean, professional interface with off-white backgrounds (#F8FAFC)
- Soft Slate (#64748b) text with Clinical Blue and Teal accents
- Rounded corners, subtle shadows, and generous whitespace
- Mobile-first design approach with tablet and desktop optimizations
- Sidebar navigation that adapts to different screen sizes

## Technical Stack

- **Backend**: Flask 2.3.3 with Flask-SocketIO for real-time communication
- **Database**: SQLAlchemy ORM with SQLite
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Cryptography**: Custom implementations of RSA, ECC, SHA-256, and HMAC
- **Fonts**: Inter (body), Plus Jakarta Sans (headings)
- **Animations**: CSS Keyframes + SVG-based particle animations
- **Styling**: Tailwind CSS with custom animations and glassmorphism

## Project Structure

```
MedLink/
├── app.py                          # Main Flask application with routes
├── models.py                       # SQLAlchemy database models
├── requirements.txt                # Python dependencies
├── medlink.db                      # SQLite database (auto-generated)
├── security/                       # Cryptography modules
│   ├── __init__.py
│   ├── rsa.py                     # RSA encryption implementation
│   ├── ecc.py                     # Elliptic Curve Cryptography
│   ├── hashing.py                 # SHA-256 & HMAC implementation
│   └── encryption_utils.py        # Utility functions for encryption
├── templates/
│   ├── base.html                  # Base template with animations & styles
│   ├── index.html                 # Landing page
│   ├── login.html                 # Secure login with 2FA
│   ├── register.html              # User registration
│   ├── dashboard.html             # Main dashboard
│   ├── chat.html                  # Real-time encrypted chat
│   ├── chat_list.html             # Chat conversations list
│   ├── profile.html               # User profile view
│   ├── edit_profile.html          # Profile editor
│   ├── admin_dashboard.html       # Admin panel
│   ├── system_log.html            # System activity log
│   ├── encrypt_demo.html          # Encryption algorithm demo
│   ├── rotate_keys.html           # Key rotation interface
│   ├── create_prescription.html    # Prescription creation
│   ├── patient_prescriptions.html  # Prescription viewer
│   ├── refer_specialist.html      # Referral creation
│   └── verify_2fa.html            # Two-factor authentication
└── README.md                       # This file
```

## Installation & Setup

### 1. Clone the Repository
```bash
cd c:\Users\prano\OneDrive\Desktop\MedLife\MedLink
```

### 2. Create Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Or using Python
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

The application will be available at: **http://localhost:5000**

## Demo Credentials

Test the application with these pre-configured accounts:

### Patient Portal
- **Email**: patient@medlink.com
- **Password**: patient123
- **Access**: View health records, send messages, view referrals, manage prescriptions

### Doctor Portal
- **Email**: doctor@medlink.com
- **Password**: doctor123
- **Access**: Create referrals, manage consultations, send prescriptions

### Specialist Portal
- **Email**: specialist@medlink.com
- **Password**: specialist123
- **Access**: Receive referrals, provide expert consultation, manage cases

### Admin Portal
- **Email**: admin@medlink.com
- **Password**: admin123
- **Access**: System administration, encryption demo, key rotation, system monitoring

## Pages Overview

### 1. Landing Page (`/`)
**Header**: Transparent navbar with logo, navigation links, and secure sign-in button
**Hero Section**: Minimalist headline "Seamless Care. Absolute Privacy" with subtext
**Portal Hub**: 3-card layout showcasing Patient, Doctor, and Specialist portals
**Features Section**: Highlights security, collaboration, and transparency
**Footer**: Links and company information

### 2. Login Page (`/login`)
**Demo Credentials Display**: Shows test login credentials for each role
**Secure Form**: Email and password inputs with validation
**Error Handling**: Displays authentication errors
**Role-Based Navigation**: Routes users to appropriate dashboard after login

### 3. Dashboard Home Page (`/dashboard`)
**Sidebar Navigation**: 
- Home (active indicator)
- Chat/Messages
- Referrals
- Settings
- Logout

**Stats Grid** (4 cards):
- Active Consultations (with trend indicator)
- Pending Referrals (with alert status)
- Verified Documents (with verification checkmark)
- System Integrity (with animated heartbeat) - Always shows 100%

**Main Content Area**:
- **Recent Activity**: Timeline-style list of medical events
  - Shows different activity types based on user role
  - Includes timestamps and activity descriptions
  - "View All Activity" button for full history

- **Security Overview**:
  - Animated heartbeat display representing system health
  - Status indicator showing "All Systems Operational"
  - HIPAA compliance information
  - Security features list (encryption, 2FA, sessions, backups)

## Design Details

### Color Palette
- **Background**: Off-White (#F8FAFC)
- **Text**: Soft Slate (#64748b)
- **Primary**: Clinical Blue (#0ea5e9)
- **Secondary**: Teal (#0d9488)
- **Success**: Green (#10b981)
- **Accents**: Various blues and teals for role-based UI

### Typography
- **Headings**: Plus Jakarta Sans (400, 500, 600, 700)
- **Body**: Inter (300, 400, 500, 600, 700)
- **Size Range**: 12px to 60px

### Animations
```css
/* Entrance animations */
@keyframes fadeInUp { ... }  /* For text elements */
@keyframes fadeIn { ... }    /* For containers */

/* Interactive animations */
@keyframes pulse { ... }     /* Subtle button pulse */
@keyframes heartbeat { ... } /* System health indicator */

/* Hover effects */
.btn-primary:hover { transform: scale(1.05); }
```

### Components

**Cards**: Elevated white cards with hover lift effect
```css
.card-elevated {
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    transition: all 0.3s ease;
}
.card-elevated:hover {
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
    transform: translateY(-4px);
}
```

**Buttons**: Smooth transitions with scale effect
```css
.btn-primary:hover {
    transform: scale(1.05);
}
```

**Navbar**: Glass morphism effect
```css
.navbar-transparent {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
}
```

## Backend Features

### Authentication
- Session-based user authentication
- Role-based access control (Patient, Doctor, Specialist)
- Protected routes (dashboard requires login)
- Logout functionality

### Mock Data
- Dynamic stats based on user role
- Role-specific activity feeds
- Realistic medical event types
- Timestamps for activities

### Routes
- `GET /` - Landing page
- `GET /login` - Login page
- `POST /login` - Handle login
- `GET /dashboard` - Dashboard (protected)
- `GET /logout` - Logout

## Customization

### Changing Colors
Edit the color values in `templates/base.html` and template files. Key CSS variables to update:
- `from-cyan-500 to-teal-600` - Primary gradient
- `bg-slate-50` - Background
- `text-slate-900` - Text color

### Adding Features
1. Update `app.py` with new routes
2. Create corresponding templates in `templates/`
3. Use the `base.html` as parent template
4. Follow the color palette and animation patterns

### Extending Dashboard
The dashboard uses a sidebar + main content layout. To add new features:
1. Add navigation item to sidebar
2. Create corresponding page/route
3. Maintain consistent design system

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance Optimizations

- Lightweight CSS framework (Tailwind)
- Minimal JavaScript (optional enhancements only)
- Optimized animations (CSS, not JavaScript-based)
- Lazy loading ready for images
- Responsive design prevents overflow

## Future Enhancements

- [ ] Real-time chat functionality
- [ ] PDF export for reports
- [ ] Calendar integration for appointments
- [ ] Email notifications
- [ ] Database integration (PostgreSQL/MySQL)
- [ ] Two-factor authentication
- [ ] User profile customization
- [ ] Advanced search and filtering
- [ ] Integration with medical APIs

## License

Proprietary - MedLink Medical Platform

## Support

For issues or questions, please contact the development team.
