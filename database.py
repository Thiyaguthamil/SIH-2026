import sqlite3
import datetime
import json

DB_NAME = "mental_health.db"

INDIAN_STATES_AND_UTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi (NCT)", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

def connect_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # Check if schema upgrade is needed
    cur.execute("PRAGMA table_info(entries)")
    columns = [row[1] for row in cur.fetchall()]
    if columns and "threat_level" not in columns:
        cur.execute("DROP TABLE IF EXISTS entries")
        cur.execute("DROP TABLE IF EXISTS alerts")
        cur.execute("DROP TABLE IF EXISTS contacts")
        cur.execute("DROP TABLE IF EXISTS nhaa_complaints")
        cur.execute("DROP TABLE IF EXISTS users")

    # 1. Users Table (Victims & Counsellors)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            password TEXT,
            case_id TEXT,
            state TEXT,
            district TEXT,
            phone TEXT,
            language TEXT DEFAULT 'en'
        )
    """)

    # 2. NHAA Complaints Table (National Helpline Against Atrocities 14566)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nhaa_complaints (
            complaint_id TEXT PRIMARY KEY,
            complainant_name TEXT,
            user_id TEXT,
            state TEXT,
            district TEXT,
            case_category TEXT,
            case_stage TEXT,
            fir_number TEXT,
            police_station TEXT,
            registration_date TEXT,
            status TEXT,
            threat_history TEXT
        )
    """)

    # 3. Entries Table with Full Multi-Factor Clinical & Socio-Legal Attributes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            case_id TEXT,
            district TEXT,
            state TEXT,
            case_category TEXT,
            case_stage TEXT,
            timestamp DATETIME,
            text TEXT,
            distress_score INTEGER,
            primary_emotion TEXT,
            emotion_json TEXT,
            risk_level TEXT,
            threat_level INTEGER DEFAULT 5,
            court_stress INTEGER DEFAULT 5,
            social_boycott INTEGER DEFAULT 5,
            economic_strain INTEGER DEFAULT 5,
            sleep_quality INTEGER DEFAULT 5,
            anxiety_level INTEGER DEFAULT 5,
            depressive_score INTEGER DEFAULT 5,
            somatic_panic INTEGER DEFAULT 5,
            voice_stress_score REAL DEFAULT 45.0,
            flagged_keywords TEXT,
            xai_json TEXT,
            interventions_json TEXT
        )
    """)

    # 4. Contacts Table (Caregiver & Authority Alerts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            user_id TEXT PRIMARY KEY,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            relationship TEXT,
            district_officer_contact TEXT
        )
    """)

    # 5. Alerts Table for Real-Time Triage & Escalation
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            case_id TEXT,
            district TEXT,
            state TEXT,
            timestamp DATETIME,
            distress_score INTEGER,
            risk_level TEXT,
            trigger_reason TEXT,
            recommended_action TEXT,
            status TEXT DEFAULT 'OPEN'
        )
    """)

    # 6. Assignments Table (State Officer manages victim-counsellor assignments)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id TEXT NOT NULL,
            counsellor_id TEXT NOT NULL,
            assigned_date TEXT,
            status TEXT DEFAULT 'ACTIVE',
            notes TEXT,
            FOREIGN KEY (victim_id) REFERENCES users(user_id),
            FOREIGN KEY (counsellor_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()

    # Pre-seed realistic demo data
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        seed_system_data(conn)

    conn.close()

def seed_system_data(conn):
    cur = conn.cursor()

    # Pre-seed Users
    users = [
        ("victim_01", "Ramesh Kumar (SC/ST Complainant)", "victim", "pass123", "NHAA-2026-8941", "Rajasthan", "Jaipur", "+91 9829012345", "en"),
        ("victim_tamil_02", "Murugan Selvam (Atrocity Survivor)", "victim", "pass123", "NHAA-2026-4412", "Tamil Nadu", "Madurai", "+91 9443123456", "ta"),
        ("victim_hindi_03", "Sunita Devi (Witness Facing Intimidation)", "victim", "pass123", "NHAA-2026-7731", "Madhya Pradesh", "Bhopal", "+91 9755123456", "hi"),
        ("counsellor_01", "Dr. Ananya Sharma (Clinical Psychologist & DLSA State Coordinator)", "counsellor", "counsel123", "", "Rajasthan", "Jaipur", "+91 9829988776", "en"),
        ("counsellor_dlsa_tn", "Adv. K. Venkatesh (Madurai DLSA Legal Counsel)", "counsellor", "counsel123", "", "Tamil Nadu", "Madurai", "+91 9444876543", "ta"),
        ("state_officer_01", "Dr. Priya Nair (State SC/ST Welfare Officer)", "state_officer", "state123", "", "Tamil Nadu", "Chennai", "+91 9840012345", "en")
    ]
    cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", users)

    # Pre-seed NHAA Registered Complaints
    complaints = [
        (
            "NHAA-2026-8941", "Ramesh Kumar", "victim_01", "Rajasthan", "Jaipur",
            "SC/ST PoA - Caste Violence & Threats", "Trial / Court Hearings",
            "FIR-412/2026", "Amer Police Station, Jaipur", "2026-08-15",
            "Special Court Trial Active", "Accused out on bail; repeated evening threats"
        ),
        (
            "NHAA-2026-4412", "Murugan Selvam", "victim_tamil_02", "Tamil Nadu", "Madurai",
            "Social Boycott & Drinking Water Denial (PoA Sec 3)", "Investigation / Chargesheet",
            "FIR-189/2026", "Usilampatti Taluk PS, Madurai", "2026-08-22",
            "Chargesheet Filing Phase", "Panchayat ostracism enforced; village shops refusing provisions"
        ),
        (
            "NHAA-2026-7731", "Sunita Devi", "victim_hindi_03", "Madhya Pradesh", "Bhopal",
            "Witness Intimidation & House Arson", "Special Court Trial",
            "FIR-092/2026", "Berasia PS, Bhopal", "2026-08-10",
            "Witness Examination Underway", "Coercion by village sarpanch to turn hostile in court"
        ),
        (
            "NHAA-2026-5120", "Prakash Ambedkar", "victim_04", "Maharashtra", "Nagpur",
            "Atrocity & Physical Assault under PoA Act", "FIR Registered",
            "FIR-301/2026", "Sitabuldi PS, Nagpur", "2026-09-01",
            "Investigation Commenced", "Initial medical exam completed; seeking police security"
        ),
        (
            "NHAA-2026-9034", "Kavitha R.", "victim_05", "Tamil Nadu", "Chennai",
            "Caste Slurs, Work Harassment & Threat to Life", "Rehabilitation & Compensation",
            "FIR-514/2026", "Ambattur Police Station, Chennai", "2026-07-18",
            "Interim Relief Disbursed (25%)", "Application submitted for DLSA victim compensation"
        ),
        (
            "NHAA-2026-3398", "Devendra Paswan", "victim_06", "Bihar", "Patna",
            "Agricultural Land Encroachment & Bodily Harm", "Investigation / Chargesheet",
            "FIR-220/2026", "Danapur Police Station, Patna", "2026-08-28",
            "Witness Statements Being Recorded", "Complainant dispossessed from ancestral field"
        ),
        (
            "NHAA-2026-6647", "Basavaraj Gowda", "victim_07", "Karnataka", "Bengaluru Urban",
            "Inter-caste Marriage Threat & Familial Boycott", "Trial / Court Hearings",
            "FIR-145/2026", "Yelahanka PS, Bengaluru", "2026-08-05",
            "Court Appearance Scheduled", "Protection order granted by High Court"
        ),
        (
            "NHAA-2026-1189", "Rajeshwari Devi", "victim_08", "Uttar Pradesh", "Varanasi",
            "Public Humiliation & Section 3(1)(r) PoA Violation", "FIR Registered",
            "FIR-678/2026", "Cantt PS, Varanasi", "2026-09-04",
            "FIR Registered via NHAA 14566", "Local DSP conducting preliminary inquiry"
        )
    ]
    cur.executemany("INSERT INTO nhaa_complaints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", complaints)

    # Pre-seed Longitudinal Check-in Logs for victim_01 (Rajasthan - Escalation Trend)
    entries_victim1 = [
        (
            "victim_01", "NHAA-2026-8941", "Jaipur", "Rajasthan",
            "SC/ST PoA - Caste Violence & Threats", "Trial / Court Hearings",
            "2026-08-30 10:30:00",
            "Felt slightly calm today. Visited the community center and met the DLSA legal aid volunteer.",
            28, "Joy", json.dumps({"joy": 0.65, "neutral": 0.25, "fear": 0.1}), "STABLE",
            2, 3, 2, 3, 7, 3, 2, 2, 18.5,
            "[]",
            json.dumps({"pct_threat": 12, "pct_court": 15, "pct_social": 10, "pct_economic": 12, "pct_sleep": 8, "pct_somatic": 8, "pct_depression": 10, "pct_voice": 8, "pct_nlp": 17}),
            json.dumps(["Routine Counseling Follow-up", "Periodic Legal Check-in"])
        ),
        (
            "victim_01", "NHAA-2026-8941", "Jaipur", "Rajasthan",
            "SC/ST PoA - Caste Violence & Threats", "Trial / Court Hearings",
            "2026-09-02 14:15:00",
            "Received summon notice for court testimony next Tuesday. Feeling anxious about facing the accused perpetrators.",
            64, "Fear", json.dumps({"fear": 0.65, "sadness": 0.25, "neutral": 0.1}), "ELEVATED",
            6, 8, 5, 6, 4, 7, 6, 6, 54.0,
            json.dumps(["court", "anxious"]),
            json.dumps({"pct_threat": 22, "pct_court": 28, "pct_social": 12, "pct_economic": 12, "pct_sleep": 8, "pct_somatic": 8, "pct_depression": 10}),
            json.dumps(["DLSA Free Legal Aid Counsel Escort Support", "Pre-Trial Anxiety Counseling via Tele-MANAS (14416)"])
        ),
        (
            "victim_01", "NHAA-2026-8941", "Jaipur", "Rajasthan",
            "SC/ST PoA - Caste Violence & Threats", "Trial / Court Hearings",
            "2026-09-05 21:40:00",
            "Threatening men arrived outside my home shouting that they will kill me if I step into court. I cannot sleep and feel completely unsafe.",
            89, "Fear", json.dumps({"fear": 0.82, "anger": 0.1, "sadness": 0.08}), "CRITICAL",
            9, 9, 7, 7, 1, 9, 8, 9, 86.5,
            json.dumps(["threat", "kill", "unsafe", "court"]),
            json.dumps({"pct_threat": 35, "pct_court": 25, "pct_social": 10, "pct_economic": 10, "pct_sleep": 8, "pct_somatic": 8, "pct_depression": 4}),
            json.dumps(["🛡️ Section 15A SC/ST PoA Act: Immediate Witness Protection & Police Security Patrol", "🧠 Tele-MANAS Emergency Trauma Consultation (14416)"])
        )
    ]

    # Pre-seed Longitudinal Check-in Logs for victim_tamil_02 (Tamil Nadu - Tamil text)
    entries_victim2 = [
        (
            "victim_tamil_02", "NHAA-2026-4412", "Madurai", "Tamil Nadu",
            "Social Boycott & Drinking Water Denial (PoA Sec 3)", "Investigation / Chargesheet",
            "2026-09-01 11:00:00",
            "ஊரில் பொதுக் கிணற்றில் தண்ணீர் எடுக்க விடாமல் சாதி ரீதியாக அச்சுறுத்துகிறார்கள். குடும்பத்தினர் மிகுந்த கவலையில் உள்ளனர்.",
            72, "Fear", json.dumps({"fear": 0.70, "sadness": 0.20, "neutral": 0.10}), "ELEVATED",
            7, 6, 9, 7, 4, 7, 6, 7, 68.0,
            json.dumps(["மிரட்டல்", "சாதி", "கவலை"]),
            json.dumps({"pct_threat": 25, "pct_court": 15, "pct_social": 30, "pct_economic": 15, "pct_sleep": 8, "pct_somatic": 7}),
            json.dumps(["⚖️ மாவட்ட ஆட்சியர் & DLSA சட்ட உதவி மூலம் உடனடி தலையீடு", "🛡️ வன்கொடுமை தடுப்புச் சட்டத்தின் கீழ் கிராம பாதுகாப்பு ரோந்து"])
        ),
        (
            "victim_tamil_02", "NHAA-2026-4412", "Madurai", "Tamil Nadu",
            "Social Boycott & Drinking Water Denial (PoA Sec 3)", "Investigation / Chargesheet",
            "2026-09-04 16:30:00",
            "டிஎஸ்பி விசாரணைக்கு வந்தார். இப்போது ஓரளவு பாதுகாப்பு உணர்கிறேன். அரசு அதிகாரிகள் உதவி செய்கிறார்கள்.",
            46, "Joy", json.dumps({"joy": 0.55, "neutral": 0.35, "sadness": 0.10}), "WATCH",
            4, 4, 6, 5, 6, 4, 4, 4, 38.0,
            json.dumps(["பாதுகாப்பு", "உதவி"]),
            json.dumps({"pct_threat": 15, "pct_court": 15, "pct_social": 25, "pct_economic": 15, "pct_sleep": 10, "pct_somatic": 10}),
            json.dumps(["வழக்கமான மனநல ஆலோசனை", "இடைக்கால நிவாரண உதவி பின்தொடர்தல்"])
        )
    ]

    for e in entries_victim1 + entries_victim2:
        cur.execute("""
            INSERT INTO entries (
                user_id, case_id, district, state, case_category, case_stage,
                timestamp, text, distress_score, primary_emotion, emotion_json, risk_level,
                threat_level, court_stress, social_boycott, economic_strain,
                sleep_quality, anxiety_level, depressive_score, somatic_panic,
                voice_stress_score, flagged_keywords, xai_json, interventions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, e)

    # Pre-seed Emergency Contacts
    contacts = [
        ("victim_01", "Dr. Ananya Sharma", "dr.ananya@statehospital.gov.in", "+91 9829988776", "DLSA Legal Aid & Psychologist", "SP Jaipur Rural Control Room (+91 141-2200112)"),
        ("victim_tamil_02", "Adv. K. Venkatesh", "venkatesh.dlsa@tn.gov.in", "+91 9444876543", "DLSA Legal Aid Advocate", "Madurai District Police Control Room (0452-2530100)"),
        ("victim_hindi_03", "Counselor Priya Verma", "priya.verma@dmhp.mp.gov.in", "+91 9755998877", "DMHP Mental Health Officer", "SP Bhopal City Office")
    ]
    cur.executemany("INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?)", contacts)

    # Pre-seed Alerts
    alerts = [
        ("victim_01", "NHAA-2026-8941", "Jaipur", "Rajasthan", "2026-09-05 21:40:00", 89, "CRITICAL", "Physical Threat & Life Intimidation Reported before Trial", "Section 15A Witness Protection Activated & Police Security Patrol", "OPEN"),
        ("victim_tamil_02", "NHAA-2026-4412", "Madurai", "Tamil Nadu", "2026-09-01 11:00:00", 72, "ELEVATED", "Severe Social Boycott & Basic Water Amenity Denial", "District Magistrate Administrative Enforcement of Civil Rights", "IN_PROGRESS"),
        ("victim_hindi_03", "NHAA-2026-7731", "Bhopal", "Madhya Pradesh", "2026-09-03 18:30:00", 78, "HIGH CONCERN", "Witness Coercion by Accused Ahead of Court Evidence", "In-Camera Trial Protection & DLSA Advocate Retainer Assigned", "OPEN")
    ]
    cur.executemany("INSERT INTO alerts (user_id, case_id, district, state, timestamp, distress_score, risk_level, trigger_reason, recommended_action, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", alerts)

    conn.commit()

# ================= HELPER DATABASE APIS =================

def authenticate_user(username, password, role="victim"):
    conn = connect_db()
    cur = conn.cursor()
    # Allow login with either the account's user_id OR its NHAA case_id,
    # since the login screen advertises both as valid identifiers.
    cur.execute("""
        SELECT user_id, name, role, case_id, state, district, phone, language FROM users
        WHERE password = ? AND role = ?
          AND (user_id = ? OR (case_id != '' AND case_id = ?))
    """, (password, role, username, username))
    user = cur.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_all_states():
    return INDIAN_STATES_AND_UTS

def get_all_nhaa_complaints(state=None):
    conn = connect_db()
    cur = conn.cursor()
    if state and state != "All States":
        cur.execute("SELECT * FROM nhaa_complaints WHERE state = ? ORDER BY registration_date DESC", (state,))
    else:
        cur.execute("SELECT * FROM nhaa_complaints ORDER BY registration_date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def register_nhaa_complaint(data):
    conn = connect_db()
    cur = conn.cursor()
    complaint_id = data.get("complaint_id") or f"NHAA-2026-{datetime.datetime.now().strftime('%H%M%S%f')[:-3]}"
    user_id = data.get("user_id") or f"victim_{complaint_id.lower().replace('-', '_')}"

    cur.execute("""
        INSERT OR REPLACE INTO nhaa_complaints (
            complaint_id, complainant_name, user_id, state, district,
            case_category, case_stage, fir_number, police_station,
            registration_date, status, threat_history
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        complaint_id,
        data.get("complainant_name", "Registered Complainant"),
        user_id,
        data.get("state", "Rajasthan"),
        data.get("district", "Jaipur"),
        data.get("case_category", "SC/ST PoA - Caste Violence & Threats"),
        data.get("case_stage", "FIR Registered"),
        data.get("fir_number", "FIR-New/2026"),
        data.get("police_station", "District Central PS"),
        datetime.datetime.now().strftime("%Y-%m-%d"),
        "FIR Registered via Integrated NHAA Portal",
        data.get("threat_history", "No prior logged threats")
    ))

    # Create associated user account if not existing
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (user_id, name, role, password, case_id, state, district, phone, language)
            VALUES (?, ?, 'victim', 'pass123', ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("complainant_name", "Registered Complainant"),
            complaint_id,
            data.get("state", "Rajasthan"),
            data.get("district", "Jaipur"),
            data.get("phone", "+91 9800000000"),
            data.get("language", "en")
        ))

    conn.commit()
    conn.close()
    return {"status": "success", "complaint_id": complaint_id, "user_id": user_id}

def save_entry(
    user_id, case_id, district, state, case_category, case_stage,
    text, score, emotion, emotion_dict, risk_level,
    threat_level=5, court_stress=5, social_boycott=5, economic_strain=5,
    sleep_quality=5, anxiety_level=5, depressive_score=5, somatic_panic=5,
    voice_stress=45.0, flagged_keywords=None, xai_dict=None, interventions_list=None
):
    conn = connect_db()
    cur = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO entries (
            user_id, case_id, district, state, case_category, case_stage,
            timestamp, text, distress_score, primary_emotion, emotion_json, risk_level,
            threat_level, court_stress, social_boycott, economic_strain,
            sleep_quality, anxiety_level, depressive_score, somatic_panic,
            voice_stress_score, flagged_keywords, xai_json, interventions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, case_id, district, state, case_category, case_stage,
        now_str, text, score, emotion, json.dumps(emotion_dict or {}), risk_level,
        threat_level, court_stress, social_boycott, economic_strain,
        sleep_quality, anxiety_level, depressive_score, somatic_panic,
        voice_stress, json.dumps(flagged_keywords or []),
        json.dumps(xai_dict or {}), json.dumps(interventions_list or [])
    ))

    # Auto-dispatch triage alert if Critical or High Concern
    if score >= 70 or risk_level in ["HIGH CONCERN", "CRITICAL"]:
        reason = f"High Multi-factor Distress ({score}/100) during {case_stage}. Threats: {threat_level}/10"
        action = interventions_list[0] if interventions_list else "Urgent Police & DLSA Follow-up"
        cur.execute("""
            INSERT INTO alerts (
                user_id, case_id, district, state, timestamp,
                distress_score, risk_level, trigger_reason, recommended_action, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """, (user_id, case_id, district, state, now_str, score, risk_level, reason, action))

    conn.commit()
    conn.close()

def get_user_history(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM entries WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_all_users(role=None):
    conn = connect_db()
    cur = conn.cursor()
    if role:
        cur.execute("SELECT user_id, name, role, case_id, state, district, phone, language FROM users WHERE role = ? ORDER BY name ASC", (role,))
    else:
        cur.execute("SELECT user_id, name, role, case_id, state, district, phone, language FROM users ORDER BY name ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_all_alerts(status=None):
    conn = connect_db()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM alerts WHERE status = ? ORDER BY timestamp DESC", (status,))
    else:
        cur.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def resolve_alert(alert_id, resolution_note=""):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE alerts SET status = 'RESOLVED' WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "alert_id": alert_id}

def save_contact(user_id, name, email, phone, relation, district_officer=""):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO contacts (user_id, contact_name, contact_email, contact_phone, relationship, district_officer_contact)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, email, phone, relation, district_officer))
    conn.commit()
    conn.close()

def get_contact(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_district_dashboard_data():
    conn = connect_db()
    cur = conn.cursor()

    # Total victims registered
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'victim'")
    total_victims = cur.fetchone()[0]

    # Active alerts
    cur.execute("SELECT COUNT(*) FROM alerts WHERE status = 'OPEN'")
    active_alerts = cur.fetchone()[0]

    # National average distress
    cur.execute("SELECT AVG(distress_score) FROM entries")
    avg_score = cur.fetchone()[0] or 0.0

    # Summary by district
    cur.execute("""
        SELECT
            e.district,
            e.state,
            COUNT(DISTINCT e.user_id) as victim_count,
            AVG(e.distress_score) as avg_distress,
            SUM(CASE WHEN e.risk_level IN ('CRITICAL', 'HIGH CONCERN', 'HIGH') THEN 1 ELSE 0 END) as high_risk_count
        FROM entries e
        GROUP BY e.district, e.state
        ORDER BY avg_distress DESC
    """)
    district_summary = [dict(r) for r in cur.fetchall()]

    # Recent alerts
    cur.execute("SELECT * FROM alerts WHERE status = 'OPEN' ORDER BY timestamp DESC LIMIT 6")
    recent_alerts = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {
        "total_victims": total_victims,
        "active_alerts": active_alerts,
        "national_avg_distress": round(avg_score, 1),
        "district_summary": district_summary,
        "recent_alerts": recent_alerts
    }

# ================= STATE OFFICER HELPER FUNCTIONS =================

def get_all_assignments():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.victim_id, a.counsellor_id, a.assigned_date, a.status, a.notes,
               v.name as victim_name, v.state as victim_state, v.district as victim_district,
               c.name as counsellor_name, c.state as counsellor_state
        FROM assignments a
        LEFT JOIN users v ON a.victim_id = v.user_id
        LEFT JOIN users c ON a.counsellor_id = c.user_id
        ORDER BY a.assigned_date DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def assign_counsellor(victim_id, counsellor_id, notes=""):
    conn = connect_db()
    cur = conn.cursor()
    # Validate victim
    cur.execute("SELECT role FROM users WHERE user_id = ?", (victim_id,))
    victim_row = cur.fetchone()
    if not victim_row:
        conn.close()
        return {"error": f"Victim '{victim_id}' not found"}
    if victim_row[0] != "victim":
        conn.close()
        return {"error": f"User '{victim_id}' is not a victim"}
    # Validate counsellor
    cur.execute("SELECT role FROM users WHERE user_id = ?", (counsellor_id,))
    counsellor_row = cur.fetchone()
    if not counsellor_row:
        conn.close()
        return {"error": f"Counsellor '{counsellor_id}' not found"}
    if counsellor_row[0] != "counsellor":
        conn.close()
        return {"error": f"User '{counsellor_id}' is not a counsellor"}
    # Check for existing ACTIVE assignment
    cur.execute("SELECT id FROM assignments WHERE victim_id = ? AND status = 'ACTIVE'", (victim_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE assignments SET status = 'REASSIGNED' WHERE id = ?", (existing[0],))
    # Create new assignment
    from datetime import datetime
    assigned_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO assignments (victim_id, counsellor_id, assigned_date, status, notes) VALUES (?, ?, ?, 'ACTIVE', ?)",
        (victim_id, counsellor_id, assigned_date, notes)
    )
    assignment_id = cur.lastrowid
    conn.commit()
    # Return the new assignment
    cur.execute("""
        SELECT a.id, a.victim_id, a.counsellor_id, a.assigned_date, a.status, a.notes,
               v.name as victim_name, c.name as counsellor_name
        FROM assignments a
        LEFT JOIN users v ON a.victim_id = v.user_id
        LEFT JOIN users c ON a.counsellor_id = c.user_id
        WHERE a.id = ?
    """, (assignment_id,))
    result = dict(cur.fetchone())
    conn.close()
    return {"success": True, "assignment": result}

def get_unassigned_victims():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.state, u.district, u.case_id, u.phone
        FROM users u
        WHERE u.role = 'victim'
        AND u.user_id NOT IN (
            SELECT victim_id FROM assignments WHERE status = 'ACTIVE'
        )
        ORDER BY u.state, u.district
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_counsellor_workload():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.state, u.district, u.phone,
               COUNT(CASE WHEN a.status = 'ACTIVE' THEN 1 END) as active_victims,
               COUNT(CASE WHEN a.status = 'REASSIGNED' THEN 1 END) as historical_assignments
        FROM users u
        LEFT JOIN assignments a ON u.user_id = a.counsellor_id
        WHERE u.role = 'counsellor'
        GROUP BY u.user_id
        ORDER BY active_victims DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_state_officer_dashboard():
    conn = connect_db()
    cur = conn.cursor()
    # Total victims
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'victim'")
    total_victims = cur.fetchone()[0]
    # Total counsellors
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'counsellor'")
    total_counsellors = cur.fetchone()[0]
    # Active cases (victims with ACTIVE assignment)
    cur.execute("SELECT COUNT(DISTINCT victim_id) FROM assignments WHERE status = 'ACTIVE'")
    active_cases = cur.fetchone()[0]
    # Unassigned victims
    cur.execute("""
        SELECT COUNT(*) FROM users WHERE role = 'victim'
        AND user_id NOT IN (SELECT victim_id FROM assignments WHERE status = 'ACTIVE')
    """)
    unassigned = cur.fetchone()[0]
    # Open alerts
    cur.execute("SELECT COUNT(*) FROM alerts WHERE status = 'OPEN'")
    open_alerts = cur.fetchone()[0]
    # Average distress
    cur.execute("SELECT AVG(distress_score) FROM entries")
    avg_score = cur.fetchone()[0] or 0.0
    # Recent assignments (last 10)
    cur.execute("""
        SELECT a.id, a.victim_id, a.counsellor_id, a.assigned_date, a.status,
               v.name as victim_name, c.name as counsellor_name
        FROM assignments a
        LEFT JOIN users v ON a.victim_id = v.user_id
        LEFT JOIN users c ON a.counsellor_id = c.user_id
        ORDER BY a.assigned_date DESC LIMIT 10
    """)
    recent_assignments = [dict(r) for r in cur.fetchall()]
    # Counsellor workload
    cur.execute("""
        SELECT u.user_id, u.name,
               COUNT(CASE WHEN a.status = 'ACTIVE' THEN 1 END) as active_victims
        FROM users u
        LEFT JOIN assignments a ON u.user_id = a.counsellor_id
        WHERE u.role = 'counsellor'
        GROUP BY u.user_id ORDER BY active_victims DESC
    """)
    counsellor_workload = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "total_victims": total_victims,
        "total_counsellors": total_counsellors,
        "active_cases": active_cases,
        "unassigned_victims": unassigned,
        "open_alerts": open_alerts,
        "avg_distress": round(avg_score, 1),
        "recent_assignments": recent_assignments,
        "counsellor_workload": counsellor_workload
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with updated multi-factor schema & pre-seeded data.")
