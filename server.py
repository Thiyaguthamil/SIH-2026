import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import predict_distress, generate_companion_reply, analyze_voice_features, analyze_behavioural_patterns
from database import (
    init_db, authenticate_user, get_all_states, get_all_nhaa_complaints,
    register_nhaa_complaint, save_entry, get_user_history, save_contact,
    get_contact, get_all_alerts, get_all_users, get_district_dashboard_data,
    resolve_alert, get_all_assignments, assign_counsellor, get_unassigned_victims,
    get_counsellor_workload, get_state_officer_dashboard
)
import traceback

app = Flask(__name__, template_folder="templates")
CORS(app)

# Ensure database is initialized at launch
init_db()

@app.route("/")
def index():
    return render_template("index.html")

# ================= AUTHENTICATION APIS =================
@app.route("/api/login", methods=["POST"])
def login_route():
    try:
        data = request.json or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        role = data.get("role", "victim")

        user = authenticate_user(username, password, role=role)
        if user:
            return jsonify({
                "status": "success",
                "user": {
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "role": user["role"],
                    "case_id": user["case_id"],
                    "state": user["state"],
                    "district": user["district"],
                    "language": user["language"]
                }
            })
        return jsonify({"status": "error", "message": "Invalid credentials or unauthorized role access."}), 401
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================= STATES & NHAA COMPLAINTS APIS =================
@app.route("/api/get_states_and_nhaa_cases", methods=["GET"])
def get_states_and_nhaa_cases_route():
    try:
        state_filter = request.args.get("state")
        states = get_all_states()
        complaints = get_all_nhaa_complaints(state=state_filter)
        return jsonify({
            "states": states,
            "complaints": complaints
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/register_nhaa_complaint", methods=["POST"])
def register_complaint_route():
    try:
        data = request.json or {}
        res = register_nhaa_complaint(data)
        return jsonify(res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================= MULTI-FACTOR DISTRESS CALCULATION =================
@app.route("/api/calculate_distress", methods=["POST"])
def calculate_distress_route():
    """Real-time calculation of multi-factor distress without database commit."""
    try:
        data = request.json or {}
        result = predict_distress(
            text=data.get("text", ""),
            threat_level=int(data.get("threat_level", 5)),
            court_stress=int(data.get("court_stress", 5)),
            social_boycott=int(data.get("social_boycott", 5)),
            economic_strain=int(data.get("economic_strain", 5)),
            sleep_quality=int(data.get("sleep_quality", 5)),
            anxiety_level=int(data.get("anxiety_level", 5)),
            depressive_score=int(data.get("depressive_score", 5)),
            somatic_panic=int(data.get("somatic_panic", 5)),
            case_stage=data.get("case_stage", "Trial / Court Hearings"),
            voice_stress=data.get("voice_stress", None),
            previous_score=int(data.get("previous_score", 50)),
            lang=data.get("lang", "en")
        )
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/submit_entry", methods=["POST"])
def submit_entry_route():
    try:
        data = request.json or {}
        user_id = data.get("user_id", "victim_01")
        case_id = data.get("case_id", "NHAA-2026-8941")
        district = data.get("district", "Jaipur")
        state = data.get("state", "Rajasthan")
        case_category = data.get("case_category", "SC/ST PoA - Caste Violence & Threats")
        case_stage = data.get("case_stage", "Trial / Court Hearings")
        text = data.get("text", "")

        threat_level = int(data.get("threat_level", 5))
        court_stress = int(data.get("court_stress", 5))
        social_boycott = int(data.get("social_boycott", 5))
        economic_strain = int(data.get("economic_strain", 5))
        sleep_quality = int(data.get("sleep_quality", 5))
        anxiety_level = int(data.get("anxiety_level", 5))
        depressive_score = int(data.get("depressive_score", 5))
        somatic_panic = int(data.get("somatic_panic", 5))
        voice_stress = data.get("voice_stress", None)
        lang = data.get("lang", "en")

        # Get previous score for delta trend
        history = get_user_history(user_id)
        prev_score = history[-1]["distress_score"] if history else 50

        ai_result = predict_distress(
            text=text,
            threat_level=threat_level,
            court_stress=court_stress,
            social_boycott=social_boycott,
            economic_strain=economic_strain,
            sleep_quality=sleep_quality,
            anxiety_level=anxiety_level,
            depressive_score=depressive_score,
            somatic_panic=somatic_panic,
            case_stage=case_stage,
            voice_stress=voice_stress,
            previous_score=prev_score,
            lang=lang
        )

        save_entry(
            user_id=user_id,
            case_id=case_id,
            district=district,
            state=state,
            case_category=case_category,
            case_stage=case_stage,
            text=text,
            score=ai_result["distress_score"],
            emotion=ai_result["primary_emotion"],
            emotion_dict=ai_result["emotion_breakdown"],
            risk_level=ai_result["risk_level"],
            threat_level=threat_level,
            court_stress=court_stress,
            social_boycott=social_boycott,
            economic_strain=economic_strain,
            sleep_quality=sleep_quality,
            anxiety_level=anxiety_level,
            depressive_score=depressive_score,
            somatic_panic=somatic_panic,
            voice_stress=ai_result["voice_stress_score"],
            flagged_keywords=ai_result["flagged_keywords"],
            xai_dict=ai_result["xai_breakdown"],
            interventions_list=ai_result["recommended_interventions"]
        )

        alert_dispatched = False
        if ai_result["distress_score"] >= 70 or ai_result["risk_level"] in ["HIGH CONCERN", "CRITICAL"]:
            alert_dispatched = True

        return jsonify({
            **ai_result,
            "alert_dispatched": alert_dispatched
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================= MULTILINGUAL CHATBOT API =================
@app.route("/chat_companion", methods=["POST"])
def chat_route():
    try:
        data = request.json or {}
        user_msg = data.get("message", "")
        lang = data.get("lang", "en")
        case_context = data.get("case_context")
        reply = generate_companion_reply(user_msg, lang=lang, case_context=case_context)
        return jsonify({"reply": reply, "lang": lang})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================= VOICE ACOUSTIC STRESS API =================
@app.route("/analyze_voice", methods=["POST"])
def analyze_voice_route():
    try:
        data = request.json or {}
        duration = float(data.get("duration", 4.5))
        pitch_variance = float(data.get("pitch_variance", 38.0))
        speech_rate = float(data.get("speech_rate", 125.0))
        pause_ratio = float(data.get("pause_ratio", 0.24))

        voice_res = analyze_voice_features(
            audio_duration_sec=duration,
            speech_rate=speech_rate,
            pitch_variance=pitch_variance,
            pause_ratio=pause_ratio
        )
        return jsonify(voice_res)
    except Exception as e:
        return jsonify({"voice_stress_score": 48.0})

# ================= BEHAVIOURAL & CLINICAL ANALYTICS =================
@app.route("/api/get_behavioural_analytics/<user_id>", methods=["GET"])
def behavioural_analytics_route(user_id):
    try:
        history = get_user_history(user_id)
        analysis = analyze_behavioural_patterns(history)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_user_analytics/<user_id>", methods=["GET"])
def get_analytics(user_id):
    try:
        history = get_user_history(user_id)
        contact = get_contact(user_id)
        behavioural = analyze_behavioural_patterns(history)
        return jsonify({
            "history": history,
            "contact": contact,
            "behavioural": behavioural
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_district_dashboard", methods=["GET"])
def district_dashboard_route():
    try:
        data = get_district_dashboard_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_users", methods=["GET"])
def get_users_route():
    try:
        role = request.args.get("role")
        users = get_all_users(role=role)
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/save_emergency_contact", methods=["POST"])
def save_contact_route():
    try:
        data = request.json or {}
        save_contact(
            user_id=data.get("user_id"),
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            relation=data.get("relation"),
            district_officer=data.get("district_officer", "")
        )
        return jsonify({"status": "success", "message": "Emergency contact & Authority details saved."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_all_alerts", methods=["GET"])
def get_alerts_route():
    try:
        alerts = get_all_alerts()
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/resolve_alert/<int:alert_id>", methods=["POST"])
def resolve_alert_route(alert_id):
    try:
        res = resolve_alert(alert_id)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= STATE OFFICER APIS =================

@app.route("/api/state_officer/dashboard", methods=["GET"])
def state_officer_dashboard():
    try:
        data = get_state_officer_dashboard()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/state_officer/assignments", methods=["GET"])
def state_officer_assignments():
    try:
        assignments = get_all_assignments()
        return jsonify(assignments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/state_officer/assign", methods=["POST"])
def state_officer_assign():
    try:
        data = request.json or {}
        victim_id = (data.get("victim_id") or "").strip()
        counsellor_id = (data.get("counsellor_id") or "").strip()
        notes = (data.get("notes") or "").strip()
        if not victim_id or not counsellor_id:
            return jsonify({"error": "Both victim_id and counsellor_id are required"}), 400
        result = assign_counsellor(victim_id, counsellor_id, notes)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/state_officer/counsellors", methods=["GET"])
def state_officer_counsellors():
    try:
        counsellors = get_counsellor_workload()
        return jsonify(counsellors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/state_officer/victims", methods=["GET"])
def state_officer_victims():
    try:
        unassigned = get_unassigned_victims()
        all_victims = get_all_users(role="victim")
        # Enrich all victims with assignment status
        assignments = get_all_assignments()
        active_map = {}
        for a in assignments:
            if a["status"] == "ACTIVE":
                active_map[a["victim_id"]] = a
        for v in all_victims:
            active = active_map.get(v["user_id"])
            if active:
                v["assigned"] = True
                v["assigned_to"] = active.get("counsellor_name", "")
                v["assigned_to_id"] = active.get("counsellor_id", "")
                v["assignment_id"] = active.get("id")
            else:
                v["assigned"] = False
                v["assigned_to"] = ""
                v["assigned_to_id"] = ""
                v["assignment_id"] = None
        return jsonify({"all_victims": all_victims, "unassigned": unassigned})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*65)
    print("AURA: AI Dynamic Mental Health Monitoring & Crisis Escalation")
    print("Problem Statement SIH26094 (SC/ST PoA & NHAA 14566 System)")
    print("Local Web Portal: http://127.0.0.1:5000")
    print("="*65 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
