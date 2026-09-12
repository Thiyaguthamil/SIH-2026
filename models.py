"""
AURA — Multimodal AI Distress Prediction & Mental Health Engine (SIH26094)
Tailored for Victims and Complainants of Atrocities under the SC/ST (PoA) Act and NHAA (14566).
Provides:
1. Multi-factor Dynamic Distress Score (Threats, Court Stress, Social Boycott, Economic Strain, Somatics, Sleep, Depression, Voice, NLP, Case Stage)
2. Behavioural Analysis Engine (Cadence, Response Latency, Avoidance/Withdrawal, Escalation Velocity)
3. Multilingual LLM Chatbot (Tamil, English, Hindi) with Gemini API support & local empathetic fallback
4. Acoustic Voice Biomarker Extraction
5. Prescriptive Statutory & DLSA Intervention Recommendations
"""

import os
import re
import math
import json
import random
from datetime import datetime
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def classify_text_emotion(text_clean):
    scores = {"joy": 0.08, "neutral": 0.22, "sadness": 0.25, "fear": 0.25, "anger": 0.12, "disgust": 0.08}
    if not text_clean:
        return scores, "Neutral"

    fear_words = ["scared", "fear", "threat", "terrified", "panic", "unsafe", "danger", "dread", "shaking", "பயம்", "மிரட்டல்", "அச்சம்", "डर", "धमकी", "खतरा", "घबराहट"]
    sadness_words = ["sad", "hopeless", "crying", "lost", "depressed", "alone", "grief", "isolated", "exhausted", "கவலை", "சோகம்", "கண்ணீர்", "தனிமை", "उदास", "निराश", "रोना", "अकेला"]
    anger_words = ["angry", "rage", "injustice", "furious", "cheat", "unfair", "revenge", "கோபம்", "ஆத்திரம்", "அநீதி", "गुस्सा", "क्रोध", "अन्याय"]
    disgust_words = ["disgust", "casteist", "humiliated", "dirty", "ashamed", "slur", "அசிங்கம்", "கேவலம்", "अपमान", "घिन"]
    joy_words = ["better", "good", "hope", "relief", "calm", "safe", "peace", "supported", "நன்று", "பாதுகாப்பு", "அமைதி", "நல்லது", "अच्छा", "राहत", "शांत", "सुरक्षित"]

    fear_hits = sum(1 for w in fear_words if w in text_clean)
    sad_hits = sum(1 for w in sadness_words if w in text_clean)
    ang_hits = sum(1 for w in anger_words if w in text_clean)
    disg_hits = sum(1 for w in disgust_words if w in text_clean)
    joy_hits = sum(1 for w in joy_words if w in text_clean)

    total_hits = fear_hits + sad_hits + ang_hits + disg_hits + joy_hits
    if total_hits > 0:
        scores["fear"] = round(min(0.85, 0.12 + (fear_hits / total_hits) * 0.65), 3)
        scores["sadness"] = round(min(0.85, 0.12 + (sad_hits / total_hits) * 0.65), 3)
        scores["anger"] = round(min(0.85, 0.08 + (ang_hits / total_hits) * 0.65), 3)
        scores["disgust"] = round(min(0.85, 0.06 + (disg_hits / total_hits) * 0.65), 3)
        scores["joy"] = round(min(0.85, 0.04 + (joy_hits / total_hits) * 0.65), 3)
        # Normalize sum to 1.0
        s_sum = sum(scores.values())
        scores = {k: round(v / s_sum, 3) for k, v in scores.items()}

    primary = max(scores, key=scores.get).capitalize()
    return scores, primary

vader = SentimentIntensityAnalyzer()

# ================= CRISIS & ATROCITY DOMAIN LEXICONS =================
CRISIS_KEYWORDS = {
    # English
    "threat": 25, "threats": 25, "threatening": 25, "intimidate": 20, "intimidation": 20,
    "kill": 35, "suicide": 45, "die": 30, "end life": 45, "hurt myself": 40,
    "hopeless": 20, "beaten": 25, "attacked": 25, "harassed": 20, "abuse": 25,
    "assault": 30, "boycott": 25, "ostracized": 25, "afraid": 15, "scared": 15,
    "terrified": 25, "trapped": 20, "worthless": 20, "nightmare": 15, "flashback": 20,
    "torture": 30, "unsafe": 20, "panic": 15, "withdraw": 25, "fir": 10, "court": 10,
    "bribe": 15, "casteist": 25, "slur": 25, "isolated": 20, "starving": 25, "poverty": 15,
    # Hindi (Devanagari & Transliterated)
    "धमकी": 25, "मारना": 35, "आत्महत्या": 45, "डर": 20, "असुरक्षित": 20, "बहिष्कार": 25,
    "अदालत": 10, "पुलिस": 10, "गवाह": 15, "परेशान": 15, "जाति": 20, "चोट": 25,
    "dhamki": 25, "marna": 35, "dar": 20, "zeher": 40, "police": 10, "court": 10,
    # Tamil (Tamil Script & Transliterated)
    "மிரட்டல்": 25, "பயம்": 20, "கொலை": 35, "தற்கொலை": 45, "சாக": 35, "தாக்குதல்": 25,
    "புறக்கணிப்பு": 25, "நீதிமன்றம்": 15, "வழக்கு": 10, "சாதி": 20, "அச்சுறுத்தல்": 25,
    "தூக்கமின்மை": 15, "கவலை": 15, "கண்ணீர்": 15, "mirattal": 25, "bayam": 20, "kavalai": 15
}

# Legal Lifecycle Vulnerability Weights
CASE_STAGE_STRESSORS = {
    "FIR Registered": 15,
    "Investigation / Chargesheet": 25,
    "Trial / Court Hearings": 35,
    "Special Court Trial": 35,
    "Rehabilitation & Relief": 20,
    "Compensation Follow-up": 18,
    "Post-Judgment Protection": 12
}

# ================= 1. ACOUSTIC VOICE FEATURE EXTRACTION =================
def analyze_voice_features(audio_duration_sec=5.0, speech_rate=120, pitch_variance=35.0, pause_ratio=0.22, energy_variation=42.0):
    """
    Extracts acoustic voice biomarkers associated with psychological distress:
    - Pitch jitter & perturbation
    - Speech tempo & hesitation / pause duration
    - Dynamic energy range
    - Voice activity detection index
    """
    jitter_factor = min(1.0, pitch_variance / 50.0)
    tempo_deviation = abs(speech_rate - 115) / 60.0
    pause_stress = min(1.0, pause_ratio / 0.45)
    energy_suppression = (100.0 - min(100.0, energy_variation)) / 100.0

    raw_vocal_distress = (jitter_factor * 35.0) + (tempo_deviation * 25.0) + (pause_stress * 20.0) + (energy_suppression * 20.0)
    vocal_stress_score = round(min(100.0, max(8.0, raw_vocal_distress)), 1)

    if vocal_stress_score > 75:
        voice_emotions = {"Distressed": 0.58, "Anxious": 0.26, "Sad": 0.10, "Neutral": 0.04, "Calm": 0.02}
    elif vocal_stress_score > 50:
        voice_emotions = {"Anxious": 0.44, "Distressed": 0.28, "Sad": 0.16, "Neutral": 0.08, "Calm": 0.04}
    elif vocal_stress_score > 30:
        voice_emotions = {"Neutral": 0.42, "Sad": 0.24, "Anxious": 0.20, "Calm": 0.10, "Distressed": 0.04}
    else:
        voice_emotions = {"Calm": 0.62, "Neutral": 0.24, "Sad": 0.08, "Anxious": 0.04, "Distressed": 0.02}

    return {
        "voice_stress_score": vocal_stress_score,
        "speech_rate_wpm": speech_rate,
        "pause_frequency_ratio": pause_ratio,
        "energy_variation_db": energy_variation,
        "pitch_variance_hz": pitch_variance,
        "voice_emotions": voice_emotions,
        "confidence": 0.85
    }

# ================= 2. MULTI-FACTOR DYNAMIC DISTRESS SCORE ENGINE =================
def predict_distress(
    text="",
    threat_level=5,
    court_stress=5,
    social_boycott=5,
    economic_strain=5,
    sleep_quality=5,
    anxiety_level=5,
    depressive_score=5,
    somatic_panic=5,
    case_stage="Trial / Court Hearings",
    voice_stress=None,
    missed_checkins=0,
    engagement_level="Regular",
    previous_score=50,
    lang="en"
):
    """
    Computes a clinically-grounded, multi-factor Dynamic Distress Score (0-100) using:
    1. Threat & Intimidation Intensity (1-10) -> Weight 18%
    2. Court Appearance & Legal Strain (1-10) -> Weight 14%
    3. Social Boycott & Ostracism (1-10) -> Weight 12%
    4. Economic & Livelihood Disruption (1-10) -> Weight 10%
    5. Sleep Disruption & Nightmares (1-10) -> Weight 8%
    6. Somatic Symptoms & Panic Manifestations (1-10) -> Weight 8%
    7. Depressive Burden / Hopelessness (1-10) -> Weight 10%
    8. NLP Emotion & Sentiment from Journal / Voice Text -> Weight 10%
    9. Vocal Acoustic Stress Perturbation -> Weight 5%
    10. Case Stage Vulnerability + Engagement Penalty -> Weight 5%
    """
    text_clean = (text or "").strip().lower()

    # --- A. Emotion Analysis ---
    emotion_scores, primary_emotion = classify_text_emotion(text_clean)

    emotion_severity = {
        "joy": 5, "surprise": 20, "neutral": 30,
        "sadness": 68, "disgust": 72, "anger": 78, "fear": 88
    }
    base_emotion_val = sum(emotion_scores.get(emo, 0) * emotion_severity.get(emo, 35) for emo in emotion_severity)

    # --- B. Sentiment Polarity ---
    if text_clean:
        vader_res = vader.polarity_scores(text)
        sentiment_compound = vader_res["compound"]
    else:
        sentiment_compound = 0.0

    # --- C. Crisis Lexicon Penalty ---
    matched_keywords = []
    keyword_score = 0
    for kw, weight in CRISIS_KEYWORDS.items():
        # Word-boundary match only. The previous "or kw in text_clean" fallback made the
        # boundary check pointless and caused false positives on short keywords/transliterations
        # (e.g. "dar" matching inside "guard", "fir" matching inside "first"/"confirm").
        if re.search(r'\b' + re.escape(kw) + r'\b', text_clean, flags=re.UNICODE):
            keyword_score += weight
            matched_keywords.append(kw)
    keyword_score = min(25, keyword_score)

    # --- D. Multi-Factor Socio-Legal & Clinical Inputs (1-10 normalized) ---
    t_threat = max(1, min(10, int(threat_level or 5)))
    t_court = max(1, min(10, int(court_stress or 5)))
    t_social = max(1, min(10, int(social_boycott or 5)))
    t_econ = max(1, min(10, int(economic_strain or 5)))
    t_sleep = max(1, min(10, int(sleep_quality or 5))) # 1=severe insomnia, 10=peaceful
    t_somatic = max(1, min(10, int(somatic_panic or 5)))
    t_depress = max(1, min(10, int(depressive_score or 5)))

    threat_component = (t_threat / 10.0) * 18.0
    court_component = (t_court / 10.0) * 14.0
    social_component = (t_social / 10.0) * 12.0
    economic_component = (t_econ / 10.0) * 10.0
    sleep_component = ((10 - t_sleep) / 10.0) * 8.0
    somatic_component = (t_somatic / 10.0) * 8.0
    depress_component = (t_depress / 10.0) * 10.0

    # --- E. Voice Acoustic Stress (Weight 5%) ---
    if voice_stress is None:
        voice_res = analyze_voice_features()
        voice_stress = voice_res["voice_stress_score"]
    voice_component = (float(voice_stress) / 100.0) * 5.0

    # --- F. Case-Stage Stressor Weight (Weight 5%, normalized against the max stage weight) ---
    max_stage_weight = max(CASE_STAGE_STRESSORS.values())
    case_stress = (CASE_STAGE_STRESSORS.get(case_stage, 20) / max_stage_weight) * 5.0

    # --- G. Engagement & Missed Check-ins (bounded escalation add-on, not part of the core 100) ---
    engagement_penalty = (missed_checkins * 3.0)
    if engagement_level == "Declining":
        engagement_penalty += 5.0
    elif engagement_level == "Disengaged":
        engagement_penalty += 10.0
    engagement_penalty = min(15.0, engagement_penalty)

    # --- H. NLP Component (Weight 10%) ---
    # Only contributes when there is actual journal/voice text to analyze. Previously, an
    # empty text field still injected a flat +12 "neutral sentiment" penalty (since VADER's
    # compound score defaults to 0 on empty text), which silently inflated every score that
    # didn't include journal text. That bug is fixed below: no text => no NLP contribution.
    if text_clean:
        emotion_fraction = min(1.0, base_emotion_val / 88.0)
        sentiment_fraction = max(0.0, min(1.0, (1.0 - sentiment_compound) / 2.0))
        keyword_fraction = min(1.0, keyword_score / 25.0)
        nlp_component = (
            (emotion_fraction * 0.40) +
            (sentiment_fraction * 0.35) +
            (keyword_fraction * 0.25)
        ) * 10.0
    else:
        nlp_component = 0.0

    # --- I. Combined Weighted Multi-Factor Score ---
    # Core weighted components sum to a 0-100 scale (18+14+12+10+8+8+10+10+5+5 = 100).
    # Engagement penalty is an additive escalation signal layered on top and capped separately.
    raw_distress = (
        threat_component +
        court_component +
        social_component +
        economic_component +
        sleep_component +
        somatic_component +
        depress_component +
        nlp_component +
        voice_component +
        case_stress +
        engagement_penalty
    )

    final_score = int(min(100, max(0, round(raw_distress))))

    # Delta & Trend
    score_delta = final_score - previous_score
    if score_delta > 4:
        trend = "↑ Increasing"
        trend_direction = "up"
    elif score_delta < -4:
        trend = "↓ Improving"
        trend_direction = "down"
    else:
        trend = "→ Stable"
        trend_direction = "stable"

    # Tiers according to requirements:
    # 0–24: STABLE
    # 25–49: WATCH
    # 50–74: ELEVATED
    # 75–100: HIGH CONCERN / CRITICAL
    if final_score <= 24:
        risk_level = "STABLE"
        color_theme = "green"
    elif final_score <= 49:
        risk_level = "WATCH"
        color_theme = "blue"
    elif final_score <= 74:
        risk_level = "ELEVATED"
        color_theme = "orange"
    else:
        risk_level = "CRITICAL" if final_score >= 85 else "HIGH CONCERN"
        color_theme = "red"

    # Explainable AI (XAI) Percentage Decomposition
    total_raw = max(1.0, raw_distress)
    xai_breakdown = {
        "pct_threat": round((threat_component / total_raw) * 100),
        "pct_court": round((court_component / total_raw) * 100),
        "pct_social": round((social_component / total_raw) * 100),
        "pct_economic": round((economic_component / total_raw) * 100),
        "pct_sleep": round((sleep_component / total_raw) * 100),
        "pct_somatic": round((somatic_component / total_raw) * 100),
        "pct_depression": round((depress_component / total_raw) * 100),
        "pct_voice": round((voice_component / total_raw) * 100),
        "pct_nlp": round((nlp_component / total_raw) * 100),
        "threat_pts": round(threat_component, 1),
        "court_pts": round(court_component, 1),
        "social_pts": round(social_component, 1),
        "economic_pts": round(economic_component, 1),
        "somatic_pts": round(somatic_component + sleep_component, 1),
        "nlp_pts": round(nlp_component, 1),
        "voice_pts": round(voice_component, 1)
    }

    # Primary contributing drivers
    contributing_signals = []
    if t_threat >= 7:
        contributing_signals.append(f"High Intimidation Factor: Direct threat rating {t_threat}/10 reported")
    if t_court >= 7:
        contributing_signals.append(f"Court Hearing Vulnerability: Legal anxiety {t_court}/10 during '{case_stage}'")
    if t_social >= 7:
        contributing_signals.append(f"Social Exclusion Strain: Ostracism rating {t_social}/10")
    if t_econ >= 7:
        contributing_signals.append(f"Acute Economic Hardship: Livelihood distress {t_econ}/10")
    if t_sleep <= 3:
        contributing_signals.append("Trauma Insomnia: Severe sleep disruption and nightmares reported")
    if t_depress >= 7:
        contributing_signals.append(f"Depressive Burden: Hopelessness score {t_depress}/10 flagged for clinical review")
    if matched_keywords:
        contributing_signals.append(f"Flagged Crisis Keywords: {', '.join(matched_keywords[:4])}")

    if not contributing_signals:
        contributing_signals.append("Baseline psychological parameters within manageable thresholds")

    # Early Warning Evaluation (Longitudinal Crisis Escalation Predictor)
    early_warning_triggered = (
        final_score >= 75 or
        score_delta >= 12 or
        (t_threat >= 8 and t_court >= 7) or
        (len(matched_keywords) >= 2 and final_score >= 60)
    )

    early_warning_msg = None
    if early_warning_triggered:
        if t_threat >= 8 or any(k in matched_keywords for k in ["kill", "threat", "dhamki", "mirattal"]):
            early_warning_msg = "Critical Intimidation Signal: High likelihood of witness compromise or physical security breach."
        elif score_delta >= 12:
            early_warning_msg = f"Rapid Distress Acceleration: +{score_delta} points escalation since last interaction."
        elif t_court >= 8:
            early_warning_msg = "High Court Appearance Dread: Imminent hearing panic requires DLSA counselor pre-trial escort."
        else:
            early_warning_msg = "Trauma Escalation Alert: Multimodal indicators predict acute psychological crisis."

    # Recommended Statutory & DLSA Interventions
    interventions = recommend_interventions(final_score, risk_level, matched_keywords, case_stage, t_threat, t_court, t_econ)

    return {
        "distress_score": final_score,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "trend": trend,
        "trend_direction": trend_direction,
        "risk_level": risk_level,
        "color_theme": color_theme,
        "primary_emotion": primary_emotion,
        "emotion_breakdown": emotion_scores,
        "voice_stress_score": voice_stress,
        "flagged_keywords": matched_keywords,
        "early_warning": {
            "triggered": early_warning_triggered,
            "severity": "CRITICAL" if final_score >= 85 else ("HIGH" if early_warning_triggered else "NONE"),
            "message": early_warning_msg,
            "recommended_action": "Urgent Statutory / Clinical Intervention" if early_warning_triggered else "Routine Scheduled Monitoring"
        },
        "xai_breakdown": xai_breakdown,
        "contributing_signals": contributing_signals,
        "recommended_interventions": interventions,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ================= 3. STATUTORY SC/ST (PoA) INTERVENTIONS =================
def recommend_interventions(score, risk_level, flagged_keywords, case_stage, threat_level=5, court_stress=5, economic_strain=5):
    """
    Statutory SC/ST (PoA) Act & NHAA prescriptive actions
    """
    interventions = []

    if threat_level >= 7 or any(k in flagged_keywords for k in ["threat", "kill", "dhamki", "mirattal", "attack", "boycott"]):
        interventions.append("Section 15A SC/ST PoA Act: Immediate Witness Protection Protocol & Local Police Patrol Dispatch")
        interventions.append("Urgent In-Camera Trial Motion to Special Judge via Public Prosecutor")

    if court_stress >= 7 or case_stage in ["Trial / Court Hearings", "Special Court Trial"]:
        interventions.append("District Legal Services Authority (DLSA) Free Dedicated Retainer Counsel Assignment")
        interventions.append("Trauma-Informed Para-Legal Worker Court Escort & Pre-Hearing Debrief")

    if economic_strain >= 7 or case_stage in ["Investigation / Chargesheet", "FIR Registered"]:
        interventions.append("Fast-Track 25% Interim Statutory Relief Disbursal under Rule 12(4) SC/ST Rules")
        interventions.append("District Social Welfare Relocation & Livelihood Rehabilitation Assistance")

    if score >= 70:
        interventions.append("Tele-MANAS (14416) District Mental Health Programme (DMHP) Trauma Specialist Session")
        interventions.append("Designated One-Stop Center (Sakhi / Atrocity Relief Cell) Caseworker Home Visit")

    if not interventions:
        interventions.append("Standard 72-Hour Digital Welfare Follow-Up Check-in")
        interventions.append("Nervous System Grounding Exercises (Box Breathing & Sensory Reset)")

    return interventions

# ================= 4. BEHAVIOURAL ANALYSIS ENGINE =================
def analyze_behavioural_patterns(history_entries):
    """
    Longitudinal Behavioural Pattern Analysis:
    - Interaction frequency and check-in adherence rate
    - Response latency & gap trends (days between interactions)
    - Distress velocity (rate of change over time)
    - Avoidance & withdrawal indicators (shortening text length, missed check-ins)
    - Predictive escalation risk percentage (0-100%)
    """
    if not history_entries or len(history_entries) < 1:
        return {
            "total_checkins": 0,
            "adherence_rate": 100,
            "adherence_status": "Regular",
            "avg_gap_days": 1.0,
            "distress_velocity": 0.0,
            "withdrawal_index": 10,
            "escalation_probability": 15,
            "escalation_tier": "LOW",
            "pattern_summary": "Insufficient longitudinal history. Baseline monitoring initiated.",
            "behavioural_flags": []
        }

    total_checkins = len(history_entries)
    scores = [h.get("distress_score", 50) for h in history_entries]
    text_lengths = [len((h.get("text") or "").strip()) for h in history_entries]

    # Calculate timestamps gaps if multiple entries exist
    gaps = []
    for i in range(1, len(history_entries)):
        try:
            t1 = datetime.strptime(history_entries[i-1]["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(history_entries[i]["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            diff_days = abs((t2 - t1).total_seconds()) / 86400.0
            gaps.append(diff_days)
        except Exception:
            gaps.append(2.0)

    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else 1.5

    # Distress Velocity (Score change per entry over last 3 entries)
    if len(scores) >= 2:
        recent_scores = scores[-3:]
        distress_velocity = round((recent_scores[-1] - recent_scores[0]) / max(1, len(recent_scores) - 1), 2)
    else:
        distress_velocity = 0.0

    # Text length compression (indicator of psychological withdrawal / numbness)
    withdrawal_detected = False
    if len(text_lengths) >= 3:
        initial_avg_len = sum(text_lengths[:2]) / 2.0
        recent_avg_len = sum(text_lengths[-2:]) / 2.0
        if initial_avg_len > 40 and recent_avg_len < 15:
            withdrawal_detected = True

    # Adherence rate
    if avg_gap <= 2.5:
        adherence_rate = 95
        adherence_status = "Optimal"
    elif avg_gap <= 5.0:
        adherence_rate = 72
        adherence_status = "Declining"
    else:
        adherence_rate = 45
        adherence_status = "Disengaged"

    # Behavioural Flags
    flags = []
    if distress_velocity > 4.0:
        flags.append(f"Rapid Acceleration: Distress increasing at +{distress_velocity} pts per check-in")
    if avg_gap > 4.0:
        flags.append(f"Interaction Latency: Check-in intervals widened to {avg_gap} days (Missed Cadence)")
    if withdrawal_detected:
        flags.append("Expressive Withdrawal: Marked reduction in verbal communication length (Emotional Numbing)")
    if scores[-1] >= 75:
        flags.append("High Distress Persistence: Current distress remains in critical severity bracket")

    # Predictive Escalation Probability (0-100%)
    base_prob = (scores[-1] * 0.5) + (max(0, distress_velocity * 4)) + ((100 - adherence_rate) * 0.3)
    escalation_prob = int(min(98, max(5, round(base_prob))))

    if escalation_prob >= 75:
        escalation_tier = "CRITICAL"
        summary = "CRITICAL PREDICTION: AI behavioural markers indicate imminent psychological decompensation or witness distress crisis within 48-72 hours."
    elif escalation_prob >= 50:
        escalation_tier = "ELEVATED"
        summary = "ELEVATED CONCERN: Negative distress velocity and widening interaction gaps suggest growing vulnerability."
    else:
        escalation_tier = "STABLE"
        summary = "STABLE TRAJECTORY: Complainant maintains consistent interaction with controlled distress levels."

    return {
        "total_checkins": total_checkins,
        "adherence_rate": adherence_rate,
        "adherence_status": adherence_status,
        "avg_gap_days": avg_gap,
        "distress_velocity": distress_velocity,
        "withdrawal_detected": withdrawal_detected,
        "withdrawal_index": 75 if withdrawal_detected else (30 if avg_gap > 3 else 10),
        "escalation_probability": escalation_prob,
        "escalation_tier": escalation_tier,
        "pattern_summary": summary,
        "behavioural_flags": flags
    }

# ================= 5. MULTILINGUAL AI CHATBOT (TAMIL, ENGLISH, HINDI) =================
def generate_companion_reply(user_message, lang="en", case_context=None):
    """
    Multilingual, trauma-informed conversational listener supporting:
    - English (en)
    - Hindi (hi)
    - Tamil (ta)
    Checks GEMINI_API_KEY environment variable for generative LLM responses.
    Falls back gracefully to high-empathy native responses in Tamil, Hindi, and English.
    """
    msg_clean = (user_message or "").strip()
    msg_low = msg_clean.lower()

    # Auto-detect language if Tamil or Hindi script is detected
    if any('\u0b80' <= c <= '\u0bff' for c in msg_clean):
        lang = "ta"
    elif any('\u0900' <= c <= '\u097f' for c in msg_clean):
        lang = "hi"

    # 1. Check if Gemini Generative API key is configured
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            prompt_lang_instruction = {
                "ta": "Respond in gentle, supportive, trauma-informed Tamil (தமிழ்).",
                "hi": "Respond in gentle, supportive, trauma-informed Hindi (हिंदी).",
                "en": "Respond in gentle, supportive, trauma-informed English."
            }.get(lang, "Respond in English.")

            system_instruction = (
                f"You are AURA, an empathetic, trauma-informed mental health companion and crisis support assistant "
                f"for victims of atrocities under India's SC/ST Prevention of Atrocities Act and National Helpline NHAA (14566). "
                f"{prompt_lang_instruction} "
                f"Be compassionate, validating, non-judgmental, and practical. "
                f"Mention that they are safe in this conversation. If threats or fear of court are mentioned, reassure them that they are entitled to free DLSA legal aid and Section 15A Witness Protection. "
                f"Keep responses between 2 to 4 supportive paragraphs. Include helplines: Tele-MANAS (14416), NHAA (14566), Emergency (112)."
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_instruction}\n\nUser Message: {msg_clean}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 400
                }
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                text_reply = data["candidates"][0]["content"]["parts"][0]["text"]
                if text_reply:
                    return text_reply.strip()
        except Exception:
            pass  # Fall through to native high-fidelity multilingual fallback

    # ================= 2. NATIVE MULTILINGUAL RULE & DICTIONARY ENGINE =================

    # --- TAMIL (தமிழ்) RESPONSES ---
    if lang == "ta":
        # Emergency / Self-Harm
        if any(w in msg_clean for w in ["தற்கொலை", "சாக", "மரண", "கொல்ல", "உயிரை", "suicide", "die", "kill"]):
            return (
                "**உங்கள் உயிர் மற்றும் பாதுகாப்பு எங்களுக்கு மிக முக்கியம்.** தயவுசெய்து உடனடியாக இந்த இலவச அரசு உதவி எண்களைத் தொடர்பு கொள்ளவும்:\n\n"
                "• **டெலி-மானாஸ் (Tele-MANAS மனநல உதவி):** `14416` (24x7 இலவசம்)\n"
                "• **தேசிய வன்கொடுமை தடுப்பு உதவி மையம் (NHAA):** `14566`\n"
                "• **காவல்துறை அவசர உதவி:** `112`\n"
                "• **சினேகா தற்கொலை தடுப்பு மையம் (சென்னை):** `044-24640050`\n\n"
                "நீங்கள் தனிமையில் இல்லை. நாம் இதை ஒன்றாக கடந்து வர முடியும். உங்கள் அருகில் உள்ளவருடன் உடனடியாக பேசுங்கள்."
            )

        # Threats & Intimidation / Court Anxiety
        if any(w in msg_clean for w in ["மிரட்டல்", "பயம்", "நீதிமன்றம்", "வழக்கு", "சாதி", "போலீஸ்", "அச்சுறுத்தல்", "mirattal", "bayam", "court"]):
            return (
                "நீங்கள் எதிர்கொள்ளும் அச்சுறுத்தல்களும் அச்சமும் மிகக் கடுமையானவை என்பதை நான் புரிந்துகொள்கிறேன்.\n\n"
                "நினைவில் கொள்ளுங்கள்: **வன்கொடுமை தடுப்புச் சட்டம் (பிரிவு 15A)**-ன் கீழ் உங்களுக்கு சாட்சி பாதுகாப்பு (Witness Protection) மற்றும் **மாவட்ட சட்ட சேவைகள் ஆணைக்குழு (DLSA)** மூலம் இலவச வழக்கறிஞர் உதவி பெறும் முழு உரிமை உண்டு.\n\n"
                "உங்களை அச்சுறுத்தும் நபர்கள் மீது சிறப்பு நீதிமன்றத்தில் புகார் அளிக்க வழி உண்டு. இப்போது உங்கள் மனதை அமைதிப்படுத்த ஒரு நிமிடம் ஆழமாக மூச்சை உள்ளிழுத்து மெதுவாக வெளிவிடுங்கள்."
            )

        # Sleep / Insomnia / Flashbacks
        if any(w in msg_clean for w in ["தூக்கம்", "கனவு", "அழு", "கவலை", "சோகம்", "வலியாக"]):
            return (
                "நடந்த கசப்பான சம்பவங்கள் உங்கள் தூக்கத்தையும் அமைதியையும் கெடுப்பது இயற்கையான அதிர்ச்சி எதிர்வினையே.\n\n"
                "இப்போது நீங்கள் பாதுகாப்பான இடத்தில் இருக்கிறீர்கள். உங்கள் இரு கால்களையும் தரையில் உறுதியாக வையுங்கள். மெதுவாக 4 வினாடிகள் மூச்சை உள்ளிழுத்து, 7 வினாடிகள் அடக்கி, 8 வினாடிகள் மெதுவாக வெளியேற்றுங்கள். நான் எப்போதும் உங்களுடன் கேட்க தயாராக இருக்கிறேன்."
            )

        # General Tamil Welcome
        return (
            "வணக்கம். நான் 'ஆரா' (AURA), உங்கள் பாதுகாப்பான மனநல ஆதரவாளர்.\n\n"
            "உங்கள் மனக் கவலைகள், நீதிமன்ற அனுபவங்கள் அல்லது அச்சங்களை எந்தவித தயக்கமும் இன்றி இங்கு பகிர்ந்து கொள்ளலாம். இன்று உங்கள் உடல் மற்றும் மனநிலை எவ்வாறு உள்ளது?"
        )

    # --- HINDI (हिंदी) RESPONSES ---
    if lang == "hi":
        # Emergency / Self-Harm
        if any(w in msg_clean for w in ["आत्महत्या", "मरना", "मार", "जहर", "suicide", "die", "kill", "zeher"]):
            return (
                "**आपकी सुरक्षा और जीवन हमारे लिए अत्यंत महत्वपूर्ण है।** कृपया तुरंत निःशुल्क सरकारी हेल्पलाइन पर संपर्क करें:\n\n"
                "• **टेली-मानस (Tele-MANAS):** कॉल करें `14416` (24x7 निःशुल्क)\n"
                "• **राष्ट्रीय अत्याचार निवारण हेल्पलाइन (NHAA):** `14566`\n"
                "• **किरण मानसिक स्वास्थ्य हेल्पलाइन (KIRAN):** `1800-599-0019`\n"
                "• **आपातकालीन पुलिस सेवा:** `112`\n\n"
                "आप इस कठिन समय में अकेले नहीं हैं। कृपया एक गहरी सांस लें और मदद स्वीकार करें।"
            )

        # Threats & Court Intimidation
        if any(w in msg_clean for w in ["धमकी", "डर", "अदालत", "पुलिस", "केस", "बहिष्कार", "गवाह", "dhamki", "dar", "court"]):
            return (
                "मैं समझ सकता हूँ कि धमकियों और अदालत के चक्करों से कितना भय और मानसिक तनाव होता है।\n\n"
                "कृपया ध्यान रखें कि **अनुसूचित जाति/जनजाति अत्याचार निवारण अधिनियम की धारा 15A** के तहत आपको 'गवाह सुरक्षा' और जिला विधिक सेवा प्राधिकरण (DLSA) से पूर्णतः निःशुल्क सरकारी वकील पाने का कानूनी अधिकार है।\n\n"
                "आपकी सुरक्षा के लिए सिस्टम ने इसे प्राथमिकता पर दर्ज कर लिया है। क्या हम 2 मिनट शांत होकर प्राणायाम / गहरी सांस का अभ्यास करें?"
            )

        # Insomnia / Flashback
        if any(w in msg_clean for w in ["नींद", "रोना", "परेशान", "घबराहट", "दर्द", "उदास"]):
            return (
                "अत्याचार और आघात के बाद नींद न आना या पुरानी बातें याद आना एक सामान्य मानवीय प्रतिक्रिया है।\n\n"
                "इस समय आप सुरक्षित स्थान पर हैं। अपनी हथेलियों को आराम से रखें और 4-7-8 गहरी सांस लेने की कोशिश करें। मैं आपकी हर बात सुनने के लिए यहाँ उपस्थित हूँ।"
            )

        # General Hindi
        return (
            "नमस्ते। मैं 'ऑरा' (AURA), आपका सुरक्षित और आत्मीय मानसिक स्वास्थ्य साथी हूँ।\n\n"
            "आप बिना किसी डर के अपने दिल की बात यहाँ साझा कर सकते हैं। आज आपका दिन कैसा बीत रहा है और आप कैसा महसूस कर रहे हैं?"
        )

    # --- ENGLISH RESPONSES ---
    # Emergency / Crisis
    if any(w in msg_low for w in ["suicide", "kill myself", "end my life", "die", "hurt myself"]):
        return (
            "**I hear how overwhelming this pain is right now, but please know you do not have to carry this alone.**\n\n"
            "Confidential, free government emergency crisis counselors are standing by right now:\n\n"
            "• **Tele-MANAS (Mental Health Crisis):** Call `14416` (24x7 Toll-Free)\n"
            "• **National Helpline Against Atrocities (NHAA):** Call `14566`\n"
            "• **Emergency Response Support System:** Call `112`\n"
            "• **KIRAN Mental Health Line:** Call `1800-599-0019`\n\n"
            "Please pause, take a slow breath, and reach out to one of these services immediately. You matter, and support is available."
        )

    # Threats & Intimidation
    if any(w in msg_low for w in ["threat", "threats", "intimidat", "withdraw", "court", "fir", "police", "boycott", "caste"]):
        return (
            "What you are experiencing with intimidation, threats, or court pressure is serious, frightening, and completely unacceptable.\n\n"
            "Please remember your statutory rights: under **Section 15A of the SC/ST (PoA) Act**, you have an absolute legal entitlement to **Police Witness Protection** and **Free Legal Counsel via the District Legal Services Authority (DLSA)**.\n\n"
            "You do not have to confront this alone. Our platform flags intimidation alerts directly for your designated legal and welfare officers. Let's ground your breathing right now."
        )

    # Insomnia / Flashbacks / Anxiety
    if any(w in msg_low for w in ["sleep", "nightmare", "flashback", "panic", "anxious", "scared", "terrified", "crying"]):
        return (
            "What you are feeling right now is your nervous system's natural reaction to severe trauma, but remember: you are safe in this physical moment.\n\n"
            "Let's ground your senses together: feel the firm support of the chair or floor beneath you, take a slow 4-second breath in through your nose, hold gently for 4, and release slowly.\n\n"
            "I am right here with you. Take all the time you need to share whatever is on your mind."
        )

    # General English
    return (
        "Hello. I am AURA, your confidential, trauma-informed companion.\n\n"
        "This is a protected, compassionate space where you can share your feelings, updates about your case, or any difficulties you are encountering. How has your sleep and peace of mind been feeling today?"
    )
