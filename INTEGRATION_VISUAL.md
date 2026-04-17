# MedLink Integration Summary - Visual Reference

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERACTION                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Send Message        Issue Referral       Download Prescription         │
│       │                    │                        │                    │
│       ▼                    ▼                        ▼                    │
│  ┌──────────┐         ┌──────────┐           ┌──────────────┐          │
│  │  Message │         │ Referral │           │   Document   │          │
│  │   Form   │         │   Form   │           │   Selector   │          │
│  └────┬─────┘         └────┬─────┘           └──────┬───────┘          │
│       │                    │                        │                    │
│       ▼                    ▼                        ▼                    │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │           FLASK ROUTES (app.py)                            │         │
│  │  /send_message    /issue_referral   /download_prescription │         │
│  └───────┬──────────────────┬──────────────────────┬──────────┘         │
│          │                  │                      │                    │
│          ▼                  ▼                      ▼                    │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │              CRYPTOGRAPHIC OPERATIONS                    │          │
│  │  ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  │          │
│  │  │ ECC Encrypt  │   │ RSA Encrypt  │  │ HMAC-SHA256  │  │          │
│  │  │ (Message)    │   │ (Referral)   │  │ (All Data)   │  │          │
│  │  └──────────────┘   └──────────────┘  └──────────────┘  │          │
│  └───────┬────────────────────┬────────────────────┬────────┘          │
│          │                    │                    │                    │
│          ▼                    ▼                    ▼                    │
│  ┌────────────────────────────────────────────────────────┐             │
│  │         DATABASE STORAGE (models.py)                   │             │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │             │
│  │  │  Message    │  │  Referral    │  │  Document    │  │             │
│  │  │  ─────────  │  │  ──────────  │  │  ─────────   │  │             │
│  │  │ encrypted_  │  │ encrypted_   │  │ encrypted_   │  │             │
│  │  │ content     │  │ content      │  │ content      │  │             │
│  │  │ mac_tag     │  │ mac_tag      │  │ mac_tag      │  │             │
│  │  │ is_verified │  │ is_verified  │  │ is_verified  │  │             │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  │             │
│  └────────┬──────────────────┬──────────────────┬─────────┘             │
│           │                  │                  │                      │
│           ▼                  ▼                  ▼                      │
│  ┌────────────────────────────────────────────────────────┐             │
│  │         DASHBOARD DISPLAY (dashboard.html)             │             │
│  │  Recent Activity      System Integrity      Live Log   │             │
│  │  ─────────────────    ──────────────────    ────────   │             │
│  │  ✓ Verified Items     100% Verified         [SUCCESS]  │             │
│  │  ⚠ Tampered Items     (if HMAC fails)       [ERROR]    │             │
│  │  📋 Messages                                [ALERT]    │             │
│  │  📋 Referrals                                          │             │
│  │  📄 Documents                                          │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Cryptographic Algorithm Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  SECURITY MODULE (security/)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  RSA (rsa.py)              ECC (ecc.py)         HASHING (hashing.py)   │
│  ──────────────            ────────────         ─────────────────      │
│  • 6-step algorithm        • Point Addition     • SHA-256 (64 rounds)  │
│  • Miller-Rabin primes     • Point Doubling     • HMAC-SHA256 (RFC 2104)
│  • Extended GCD            • Scalar Multiply    • Password Hashing      │
│  • Modular inverse         • Double-and-Add     • Constant-time compare │
│  • Fast exponentiation     • Curve validation   • Random salt (16 bytes)│
│  • Encryption/Decryption   • Group operations   • Bitwise operations   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│              INTEGRATION WITH FLASK APPLICATION                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATABASE MODELS                   FLASK ROUTES                         │
│  ────────────────                  ────────────                         │
│  User                              POST /send_message                    │
│  ├─ rsa_public_key                  ├─ Encrypt with ECC                 │
│  ├─ rsa_private_key                 ├─ Generate HMAC                    │
│  ├─ ecc_public_key                  └─ Store in database                │
│  └─ ecc_private_key                                                     │
│                                     POST /issue_referral                │
│  Message                           ├─ Hash with SHA-256                │
│  ├─ encrypted_content              ├─ Encrypt with RSA                 │
│  ├─ mac_tag                        ├─ Generate HMAC                    │
│  └─ is_verified                    └─ Store in database                │
│                                                                          │
│  Referral                          GET /download_prescription           │
│  ├─ encrypted_content              ├─ Verify HMAC                      │
│  ├─ mac_tag                        ├─ Decrypt with ECC                 │
│  └─ is_verified                    └─ Return plaintext                 │
│                                                                          │
│  Document                          POST /admin/simulate-attack          │
│  ├─ encrypted_content              ├─ Flip random bit                  │
│  ├─ mac_tag                        ├─ Keep MAC unchanged               │
│  └─ is_verified                    └─ Next view: HMAC fails!           │
│                                                                          │
│                                     GET /system-log                     │
│                                     └─ Return last 50 log entries       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Feature Matrix

```
┌────────────────┬──────────────┬──────────────┬──────────────┬────────────┐
│ Feature        │ Encryption   │ Signing      │ Integrity    │ Verification
├────────────────┼──────────────┼──────────────┼──────────────┼────────────┤
│ Messages       │ ECC          │ -            │ HMAC-SHA256  │ ✓ Auto    │
│ Referrals      │ RSA          │ RSA          │ HMAC-SHA256  │ ✓ Auto    │
│ Prescriptions  │ ECC (LSB)    │ -            │ HMAC-SHA256  │ ✓ Auto    │
│ Passwords      │ SHA-256+Salt │ -            │ N/A          │ ✓ Implicit│
│ System Log     │ Plain text   │ -            │ N/A          │ -         │
└────────────────┴──────────────┴──────────────┴──────────────┴────────────┘
```

---

## 🎯 Button Functionality

```
DASHBOARD BUTTONS
├─ 📋 Issue Referral
│  ├─ Opens modal form
│  ├─ Select recipient (patient/specialist)
│  ├─ Enter referral content
│  └─ ON SUBMIT:
│     ├─ Hash content with SHA-256
│     ├─ Encrypt with RSA
│     ├─ Generate HMAC
│     ├─ Store in database
│     └─ Log: [SUCCESS] Referral signed & encrypted
│
├─ 📥 Download Prescription
│  ├─ Opens modal with document selector
│  ├─ Select document from list
│  └─ ON SUBMIT:
│     ├─ Retrieve document from database
│     ├─ Verify HMAC
│     │  └─ If fails → Error: "Data Tampered"
│     ├─ Decrypt with ECC
│     └─ Return plaintext prescription
│
├─ ⚠️ Attack Simulator
│  ├─ Opens modal with target selector
│  ├─ Select message/referral to attack
│  └─ ON SUBMIT:
│     ├─ Find record in database
│     ├─ Flip random bit in encrypted_content
│     ├─ Keep mac_tag unchanged (crucial!)
│     ├─ Save to database
│     ├─ Log: [ALERT] ATTACK SIMULATION
│     └─ Next view: HMAC fails → RED WARNING
│
└─ 🔄 Refresh Log
   └─ ON CLICK: Fetch latest 50 log entries
```

---

## 📱 UI Components

```
LIVE SYSTEM STATUS PANEL
┌────────────────────────────────────────────────────────────────┐
│ 🔐 Live System Status                              ● Live      │
├────────────────────────────────────────────────────────────────┤
│ [INFO] 18:56:55 - Generated RSA & ECC keys for all users       │
│ [SUCCESS] 18:57:12 - Message encrypted with HMAC-SHA256        │
│ [SUCCESS] 18:57:45 - Referral signed & encrypted               │
│ [ALERT] 18:58:20 - ATTACK SIMULATION: Message 1 corrupted     │
│ [ALERT] 18:58:25 - HMAC Mismatch Detected - DATA TAMPERED     │
│                                                                │
│ [4 ACTION BUTTONS]                                             │
└────────────────────────────────────────────────────────────────┘

RECENT ACTIVITY
┌────────────────────────────────────────────────────────────────┐
│ 📋 Referral to Dr. Specialist              ✓ Verified  18:57  │
│ 💬 Message from Dr. Doctor                 ✓ Verified  18:56  │
│ 📋 Referral from Dr. Doctor                ⚠ Tampered! 18:55  │
│ 📄 Lab Result Uploaded                     ✓ Verified  18:54  │
└────────────────────────────────────────────────────────────────┘

CHAT INTERFACE
┌────────────────────────────────────────────────────────────────┐
│ Dr. Doctor                                                     │
│ 🔒 End-to-End Encrypted (ECC + HMAC)                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│                    ┌──────────────────────┐                   │
│                    │ Sure, feel free to ask│ ✓ Verified 18:56 │
│                    └──────────────────────┘                   │
│                                                                │
│ ┌──────────────────────────┐                                  │
│ │ I have a follow-up       │ ✓ Verified 18:57                │
│ │ question                 │                                  │
│ └──────────────────────────┘                                  │
│                                                                │
│ [Message input field] [Send]                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Verification Flow

```
WHEN DATA IS VIEWED:
├─ 1. Retrieve encrypted_content + mac_tag from database
├─ 2. Recalculate: expected_mac = HMAC(encrypted_content)
├─ 3. Compare: stored_mac_tag == expected_mac?
│  │
│  ├─ YES (Data unchanged)
│  │  ├─ Set is_verified = True
│  │  ├─ Display: ✓ Verified (GREEN badge)
│  │  └─ Log: [SUCCESS] HMAC verification passed
│  │
│  └─ NO (Data modified!)
│     ├─ Set is_verified = False
│     ├─ Display: ⚠ Tampered (RED badge)
│     └─ Log: [ALERT] HMAC Mismatch Detected - DATA TAMPERED
│
└─ 4. Return data to user with verification status

CONSTANT-TIME COMPARISON:
├─ Use XOR to compare mac values
├─ Compare ALL bytes (don't short-circuit)
└─ Prevents timing attack vulnerabilities
```

---

## 🚀 Sample Request/Response

```
REQUEST: POST /send_message
─────────────────────────────────────────
Form Data:
  receiver_id: 2
  message: "I have a follow-up question"

PROCESSING:
─────────────────────────────────────────
1. Encrypt "I have a follow-up question" with ECC
2. encrypted_content = "xxxxxxxx..."
3. hmac_key = "message_1"
4. mac_tag = HMAC-SHA256("message_1", "I have...") = "yyyyyyyy..."
5. Create Message record in database
6. Log: "[SUCCESS] Message encrypted with HMAC-SHA256"

RESPONSE:
─────────────────────────────────────────
{
  "success": true,
  "message_id": 5
}

SYSTEM LOG:
─────────────────────────────────────────
[SUCCESS] 18:57:12 - Message encrypted with HMAC-SHA256: 
Patient → Dr. Doctor | MAC: yyyyyyyy...
```

---

## 📈 Metrics

```
CODE ADDITIONS:
┌────────────────────────┬───────┐
│ File                   │ Lines │
├────────────────────────┼───────┤
│ app.py (new routes)    │  450+ │
│ models.py (key storage)│   50+ │
│ dashboard.html (UI)    │  200+ │
│ chat.html (new)        │  120+ │
│ DOCUMENTATION          │ 2000+ │
└────────────────────────┴───────┘

ROUTES REGISTERED:
┌────────────────────────────────────────┐
│ GET   /                                │
│ GET   /login                           │
│ POST  /login                           │
│ GET   /dashboard                       │
│ GET   /logout                          │
│ POST  /send_message                    │
│ GET   /chat/<id>                       │
│ POST  /issue_referral                  │
│ GET   /download_prescription/<id>      │
│ POST  /admin/simulate-attack/<id>      │
│ GET   /system-log                      │
│ (+ static file routes)                 │
└────────────────────────────────────────┘

CRYPTOGRAPHIC FUNCTIONS USED:
┌────────────────────────────────┐
│ generate_keys()                │
│ encrypt()                      │
│ decrypt()                      │
│ manual_sha256()                │
│ hmac_sha256()                  │
│ generate_mac()                 │
│ verify_mac()                   │
│ hash_password()                │
│ verify_password()              │
│ EllipticCurve.point_addition() │
│ EllipticCurve.point_doubling() │
│ EllipticCurve.scalar_mult()    │
└────────────────────────────────┘
```

---

## ✅ Verification Checklist

- ✓ RSA keys generated for every user
- ✓ ECC keys generated for every user
- ✓ Message encryption working (ECC)
- ✓ Referral signing working (RSA)
- ✓ HMAC generation working (all data)
- ✓ HMAC verification working (auto on load)
- ✓ Attack simulator working (bit flipping)
- ✓ System log working (real-time updates)
- ✓ Dashboard UI updated with buttons
- ✓ Chat interface with verification badges
- ✓ Modal forms for all actions
- ✓ Database schema correct
- ✓ App imports successfully
- ✓ All 12 routes registered
- ✓ Database initializes correctly

---

**Status: ✅ FULLY INTEGRATED AND OPERATIONAL**
