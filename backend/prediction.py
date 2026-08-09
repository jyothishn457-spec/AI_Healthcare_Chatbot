"""
prediction.py
Deterministic symptom -> condition prediction service.

Unlike the free-text chatbot, this module takes a STRUCTURED symptom checklist
and produces a ranked list of possible conditions. It uses a curated medical
knowledge base (symptom -> condition weights) plus red-flag detection.

Design goals:
  - Deterministic and offline: no LLM call, so results are fast, consistent
    and demo-friendly.
  - Honest about uncertainty: every result is labelled with a confidence
    bucket (High / Moderate / Low) and always marked "informational, not
    diagnostic".

The knowledge base is intentionally conservative: it covers common conditions
with clear symptom signatures. It is NOT a diagnosis.
"""

DISCLAIMER = (
    "This tool is for educational/informational purposes only and is NOT a "
    "diagnosis. It does not replace a medical professional. Please see a "
    "qualified doctor for any persistent, worsening or concerning symptoms."
)

# The ordered list of symptoms exposed to the UI. Each symptom has a human
# label and a group so the checklist can be rendered in sections.
SYMPTOMS: dict[str, dict] = {
    # General
    "fever": {"label": "Fever", "group": "General"},
    "chills": {"label": "Chills or shivering", "group": "General"},
    "fatigue": {"label": "Fatigue or weakness", "group": "General"},
    "loss_of_appetite": {"label": "Loss of appetite", "group": "General"},
    "weight_loss": {"label": "Unexplained weight loss", "group": "General"},
    # Pain
    "headache": {"label": "Headache", "group": "Pain"},
    "body_ache": {"label": "Body or muscle aches", "group": "Pain"},
    "joint_pain": {"label": "Joint pain", "group": "Pain"},
    "back_pain": {"label": "Lower back pain", "group": "Pain"},
    "chest_pain": {"label": "Chest pain or tightness", "group": "Pain"},
    "abdominal_pain": {"label": "Abdominal (belly) pain", "group": "Pain"},
    # Respiratory
    "sore_throat": {"label": "Sore throat", "group": "Respiratory"},
    "cough": {"label": "Cough", "group": "Respiratory"},
    "runny_nose": {"label": "Runny or stuffy nose", "group": "Respiratory"},
    "sneezing": {"label": "Sneezing", "group": "Respiratory"},
    "shortness_of_breath": {"label": "Shortness of breath", "group": "Respiratory"},
    # Digestive
    "nausea": {"label": "Nausea", "group": "Digestive"},
    "vomiting": {"label": "Vomiting", "group": "Digestive"},
    "diarrhea": {"label": "Diarrhea", "group": "Digestive"},
    "constipation": {"label": "Constipation", "group": "Digestive"},
    # Cardiovascular
    "dizziness": {"label": "Dizziness or lightheadedness", "group": "Cardiovascular"},
    "palpitations": {"label": "Racing heartbeat (palpitations)", "group": "Cardiovascular"},
    # Skin
    "rash": {"label": "Skin rash", "group": "Skin"},
    "swelling": {"label": "Swelling in feet or ankles", "group": "Skin"},
    # Metabolic
    "increased_thirst": {"label": "Increased thirst", "group": "Metabolic"},
    "frequent_urination": {"label": "Frequent urination", "group": "Metabolic"},
    # Sensory / mental
    "blurred_vision": {"label": "Blurred vision", "group": "Sensory"},
    "insomnia": {"label": "Trouble sleeping", "group": "Mental health"},
    "anxiety": {"label": "Anxiety or nervousness", "group": "Mental health"},
}

# Each condition lists symptom -> weight. Weights reflect how strongly a
# symptom points toward that condition (0 = absent from its signature).
CONDITIONS: dict[str, dict] = {
    "common_cold": {
        "name": "Common cold",
        "symptoms": {
            "runny_nose": 3, "sneezing": 3, "sore_throat": 2, "cough": 2,
            "headache": 1, "fatigue": 1,
        },
        "explanation": (
            "The common cold is a viral infection of the nose and throat. "
            "It usually causes a runny nose, sneezing and a mild sore throat, "
            "with low or no fever."
        ),
        "next_steps": (
            "Rest, drink plenty of fluids and use over-the-counter relief for "
            "a stuffy nose. It usually clears in 7-10 days. See a doctor if it "
            "worsens or lasts longer than 10 days."
        ),
    },
    "influenza": {
        "name": "Influenza (flu)",
        "symptoms": {
            "fever": 3, "chills": 2, "body_ache": 3, "fatigue": 3,
            "headache": 2, "cough": 2, "sore_throat": 1, "runny_nose": 1,
        },
        "explanation": (
            "Flu is a contagious respiratory illness that typically starts "
            "suddenly with fever, chills, muscle aches and tiredness, often "
            "with a cough."
        ),
        "next_steps": (
            "Rest and hydrate well. Fever-reducers can help. Flu is most "
            "concerning in young children, older adults and people with "
            "chronic conditions - see a doctor promptly if that applies to you."
        ),
    },
    "covid19": {
        "name": "COVID-19",
        "symptoms": {
            "fever": 3, "cough": 3, "fatigue": 3, "sore_throat": 2,
            "headache": 2, "shortness_of_breath": 2, "body_ache": 1,
            "runny_nose": 1,
        },
        "explanation": (
            "COVID-19 is a viral illness that often brings fever, a new "
            "continuous cough, tiredness and sometimes shortness of breath."
        ),
        "next_steps": (
            "Isolate from others and get tested. If you have trouble "
            "breathing, persistent chest pain or confusion, seek emergency "
            "care immediately."
        ),
    },
    "strep_throat": {
        "name": "Strep throat",
        "symptoms": {
            "sore_throat": 3, "fever": 2, "headache": 1, "chills": 1,
            "fatigue": 1,
        },
        "explanation": (
            "Strep throat is a bacterial throat infection causing a painful "
            "sore throat, often with fever. It may make swallowing difficult."
        ),
        "next_steps": (
            "A doctor can confirm it with a quick test and prescribe "
            "antibiotics if needed. Untreated strep can cause complications, "
            "so see a doctor if your throat is very painful with fever."
        ),
    },
    "migraine": {
        "name": "Migraine",
        "symptoms": {
            "headache": 3, "nausea": 2, "vomiting": 1, "dizziness": 1,
            "blurred_vision": 1,
        },
        "explanation": (
            "A migraine is a severe, often one-sided headache that can come "
            "with nausea, light sensitivity and visual disturbances."
        ),
        "next_steps": (
            "Rest in a dark, quiet room and stay hydrated. If headaches are "
            "frequent, severe or suddenly change, see a doctor. A sudden "
            "'worst-ever' headache is an emergency."
        ),
    },
    "tension_headache": {
        "name": "Tension headache",
        "symptoms": {
            "headache": 3, "fatigue": 1, "insomnia": 1, "anxiety": 1,
        },
        "explanation": (
            "Tension headaches are the most common type - a dull, pressing "
            "pain on both sides of the head, often linked to stress, poor "
            "sleep or screen time."
        ),
        "next_steps": (
            "Rest, hydration, gentle stretching and stress management usually "
            "help. See a doctor if headaches become frequent."
        ),
    },
    "gastroenteritis": {
        "name": "Gastroenteritis (stomach bug)",
        "symptoms": {
            "nausea": 3, "vomiting": 3, "diarrhea": 3, "abdominal_pain": 2,
            "fever": 1, "fatigue": 1, "loss_of_appetite": 1,
        },
        "explanation": (
            "Gastroenteritis is an infection of the stomach and intestines, "
            "causing nausea, vomiting and diarrhea. It is usually viral and "
            "short-lived."
        ),
        "next_steps": (
            "Prevent dehydration with small, frequent sips of fluids or oral "
            "rehydration solution. Seek medical care if you cannot keep "
            "liquids down, see blood in stool, or signs of dehydration "
            "(dizziness, very dark urine)."
        ),
    },
    "appendicitis": {
        "name": "Appendicitis (possible - urgent)",
        "symptoms": {
            "abdominal_pain": 3, "nausea": 2, "vomiting": 2, "loss_of_appetite": 2,
            "fever": 1,
        },
        "explanation": (
            "Appendicitis is an inflammation of the appendix causing pain "
            "that often starts around the belly button and moves to the "
            "lower-right abdomen, worsening with movement."
        ),
        "next_steps": (
            "Appendicitis requires URGENT medical evaluation - do not wait. "
            "Go to an emergency department if you have severe belly pain that "
            "is worsening or moving to the right lower side."
        ),
        "urgent": True,
    },
    "gerd": {
        "name": "Acid reflux (GERD)",
        "symptoms": {
            "nausea": 1, "chest_pain": 2, "abdominal_pain": 1, "cough": 1,
        },
        "explanation": (
            "Acid reflux (GERD) causes stomach acid to flow back into the "
            "food pipe, often producing heartburn or a burning chest "
            "discomfort after eating."
        ),
        "next_steps": (
            "Eat smaller meals, avoid lying down right after eating and limit "
            "spicy/fatty foods. Persistent chest pain should always be checked "
            "by a doctor to rule out heart problems."
        ),
    },
    "uti": {
        "name": "Urinary tract infection (UTI)",
        "symptoms": {
            "frequent_urination": 3, "fever": 1, "abdominal_pain": 2,
            "fatigue": 1, "chills": 1,
        },
        "explanation": (
            "A UTI is an infection of the urinary tract. Common signs include "
            "a frequent, urgent need to urinate and discomfort in the lower "
            "belly or when passing urine."
        ),
        "next_steps": (
            "See a doctor - UTIs usually need antibiotics. Untreated, an "
            "infection can spread to the kidneys."
        ),
    },
    "diabetes": {
        "name": "Type 2 diabetes (possible)",
        "symptoms": {
            "increased_thirst": 3, "frequent_urination": 3, "fatigue": 2,
            "weight_loss": 2, "blurred_vision": 1,
        },
        "explanation": (
            "High blood sugar can cause increased thirst, frequent urination "
            "and tiredness. These symptoms can develop gradually."
        ),
        "next_steps": (
            "Get a blood sugar test - a simple blood test can confirm. "
            "Left untreated, high blood sugar can cause serious complications, "
            "so make an appointment soon."
        ),
    },
    "hypertension": {
        "name": "High blood pressure (possible)",
        "symptoms": {
            "headache": 2, "dizziness": 2, "palpitations": 2, "chest_pain": 1,
            "blurred_vision": 1,
        },
        "explanation": (
            "High blood pressure often has no symptoms and is found during a "
            "check-up. Some people experience headaches, dizziness or a "
            "racing heart."
        ),
        "next_steps": (
            "Have your blood pressure measured. A sudden very high reading "
            "with headache, chest pain or vision changes is an emergency."
        ),
    },
    "anemia": {
        "name": "Anemia (possible)",
        "symptoms": {
            "fatigue": 3, "dizziness": 2, "palpitations": 2,
            "shortness_of_breath": 2, "headache": 1,
        },
        "explanation": (
            "Anemia means low red blood cells, causing tiredness, weakness and "
            "shortness of breath on exertion."
        ),
        "next_steps": (
            "A simple blood test (CBC) can confirm. Your doctor can find the "
            "cause and recommend iron or other treatment."
        ),
    },
    "hypothyroidism": {
        "name": "Underactive thyroid (possible)",
        "symptoms": {
            "fatigue": 3, "weight_loss": 0, "constipation": 1, "insomnia": 1,
        },
        "explanation": (
            "An underactive thyroid slows the metabolism, causing fatigue, "
            "weight gain, feeling cold and constipation."
        ),
        "next_steps": (
            "A thyroid blood test can confirm. Treatment is simple and "
            "effective, so see your doctor if fatigue is persistent."
        ),
    },
    "asthma": {
        "name": "Asthma (possible)",
        "symptoms": {
            "shortness_of_breath": 3, "cough": 2, "chest_pain": 2,
            "fatigue": 1,
        },
        "explanation": (
            "Asthma causes the airways to narrow, leading to wheezing, cough "
            "and shortness of breath, sometimes worse at night."
        ),
        "next_steps": (
            "See a doctor for a breathing test. If breathing becomes very "
            "difficult or lips turn blue, call emergency services."
        ),
    },
    "anxiety": {
        "name": "Anxiety (possible)",
        "symptoms": {
            "palpitations": 3, "anxiety": 3, "shortness_of_breath": 2,
            "dizziness": 2, "insomnia": 2, "fatigue": 1, "chest_pain": 1,
        },
        "explanation": (
            "Anxiety can cause physical symptoms such as a racing heart, "
            "trouble breathing and dizziness, in addition to worry and poor "
            "sleep."
        ),
        "next_steps": (
            "Talk to a healthcare professional. Breathing exercises and "
            "regular physical activity help, and therapy can be very effective."
        ),
    },
    "depression": {
        "name": "Depression (possible)",
        "symptoms": {
            "fatigue": 3, "insomnia": 3, "loss_of_appetite": 2, "anxiety": 2,
            "weight_loss": 1,
        },
        "explanation": (
            "Depression can show up as persistent low energy, trouble "
            "sleeping, loss of appetite and loss of interest in usual "
            "activities."
        ),
        "next_steps": (
            "Reach out to a doctor or counsellor - treatment works. If you "
            "are having thoughts of harming yourself, contact a crisis line "
            "or emergency services now."
        ),
    },
    "allergies": {
        "name": "Allergies (hay fever)",
        "symptoms": {
            "sneezing": 3, "runny_nose": 3, "cough": 1, "fatigue": 1,
        },
        "explanation": (
            "Allergic rhinitis (hay fever) is triggered by allergens like "
            "pollen, causing sneezing and a runny, itchy nose."
        ),
        "next_steps": (
            "Avoid triggers, rinse your nose with saline, and try "
            "over-the-counter antihistamines. See a doctor if symptoms "
            "interfere with daily life."
        ),
    },
    "dengue": {
        "name": "Dengue (possible)",
        "symptoms": {
            "fever": 3, "headache": 3, "body_ache": 3, "joint_pain": 2,
            "rash": 2, "fatigue": 2, "nausea": 1,
        },
        "explanation": (
            "Dengue is a mosquito-borne viral infection causing high fever, "
            "severe headache, pain behind the eyes and intense muscle/joint "
            "aches."
        ),
        "next_steps": (
            "Rest and hydrate. Go to a doctor for a blood test. Seek urgent "
            "care for severe belly pain, vomiting blood, or bleeding gums."
        ),
    },
    "malaria": {
        "name": "Malaria (possible)",
        "symptoms": {
            "fever": 3, "chills": 3, "headache": 2, "nausea": 2,
            "body_ache": 2, "fatigue": 1,
        },
        "explanation": (
            "Malaria is a mosquito-borne infection causing cycles of fever, "
            "chills and sweating, often with headache and nausea."
        ),
        "next_steps": (
            "Malaria needs prompt medical treatment - see a doctor for a "
            "blood test, especially after travel to a risk area."
        ),
    },
    "typhoid": {
        "name": "Typhoid fever (possible)",
        "symptoms": {
            "fever": 3, "abdominal_pain": 2, "fatigue": 2, "loss_of_appetite": 2,
            "diarrhea": 1, "constipation": 1, "headache": 1,
        },
        "explanation": (
            "Typhoid is a bacterial infection causing a sustained high fever, "
            "tummy pain and weakness, often after contaminated food or water."
        ),
        "next_steps": (
            "See a doctor - typhoid is treated with antibiotics. Untreated it "
            "can be serious."
        ),
    },
    "chickenpox": {
        "name": "Chickenpox (possible)",
        "symptoms": {
            "rash": 3, "fever": 2, "fatigue": 2, "body_ache": 1, "headache": 1,
        },
        "explanation": (
            "Chickenpox is a viral infection causing an itchy blister-like "
            "rash, usually starting on the chest/back and face, with mild "
            "fever."
        ),
        "next_steps": (
            "Keep blisters clean and avoid scratching. Most people recover at "
            "home, but see a doctor if you are pregnant, immunocompromised, "
            "or if the rash becomes very painful or infected."
        ),
    },
    "sinusitis": {
        "name": "Sinusitis (sinus infection)",
        "symptoms": {
            "runny_nose": 2, "headache": 3, "cough": 1, "fever": 1,
            "fatigue": 1,
        },
        "explanation": (
            "Sinusitis is inflammation of the sinus cavities, causing facial "
            "pressure, a blocked nose and a dull headache."
        ),
        "next_steps": (
            "Steam inhalation, saline rinses and rest usually help. See a "
            "doctor if symptoms last more than 10 days or are severe."
        ),
    },
}

# Symptoms that should always trigger urgent-care advice, regardless of the
# ranked conditions. Each entry carries a plain-language message.
RED_FLAGS: dict[str, str] = {
    "chest_pain": (
        "Chest pain or tightness can be a sign of a serious heart problem. "
        "If it is sudden, severe, or spreads to the arm or jaw, call "
        "emergency services immediately."
    ),
    "shortness_of_breath": (
        "Severe or sudden shortness of breath can be life-threatening. If you "
        "struggle to breathe, feel breathless at rest, or your lips turn "
        "blue, seek emergency care now."
    ),
}

# Guidance shown regardless of the specific conditions found.
GENERAL_ADVICE = (
    "Your symptom pattern may match common conditions, but many illnesses "
    "share the same symptoms. Track how you feel over the next 24-48 hours "
    "and see a doctor if symptoms persist, worsen or new ones appear."
)

# Extra guidance if the top match is weak (low confidence across the board).
LOW_CONFIDENCE_ADVICE = (
    "The symptoms you selected do not clearly match any condition in our "
    "knowledge base. This may be normal variation, but if you are worried, "
    "a doctor is the best person to ask."
)


# ---------------------------------------------------------------- public API
def list_symptoms() -> list[dict]:
    """Return every symptom the API accepts, for rendering the checklist."""
    return [
        {"id": sid, "label": meta["label"], "group": meta["group"]}
        for sid, meta in SYMPTOMS.items()
    ]


def run_prediction(
    symptom_ids: list[str],
    age_group: str | None = None,
    sex: str | None = None,
    duration: str | None = None,
) -> dict:
    """
    Score the selected symptoms against the knowledge base.

    Returns a structured payload with:
      - ``ranked_conditions``: top matches, each with name, confidence bucket,
        match ratio (0-1), plain-language explanation and next-step guidance.
      - ``urgent_care_advice``: set when a red-flag symptom is present.
      - ``informational``: always True - this is never a diagnosis.
      - metadata (age group, sex, duration) echoed for the user's records.
    """
    selected = [s for s in symptom_ids if s in SYMPTOMS]

    scored: list[dict] = []
    for condition_id, cond in CONDITIONS.items():
        signature_weight = sum(cond["symptoms"].values())
        matched_weight = sum(w for s, w in cond["symptoms"].items() if s in selected)
        if matched_weight == 0:
            continue
        match = matched_weight / signature_weight if signature_weight else 0.0
        scored.append(
            {
                "id": condition_id,
                "name": cond["name"],
                "match": round(match, 2),
                "confidence": _confidence_bucket(match),
                "explanation": cond["explanation"],
                "next_steps": cond["next_steps"],
                "urgent": bool(cond.get("urgent", False)),
            }
        )

    # Rank by match ratio, breaking ties by matched weight.
    scored.sort(key=lambda c: (c["match"], _matched_weight(c["id"], selected)), reverse=True)
    ranked = scored[:5]

    urgent_advice = []
    for sid in RED_FLAGS:
        if sid in selected:
            urgent_advice.append(RED_FLAGS[sid])

    return {
        "informational": True,
        "disclaimer": DISCLAIMER,
        "ranked_conditions": ranked,
        "urgent_care_advice": urgent_advice,
        "general_advice": GENERAL_ADVICE if ranked else LOW_CONFIDENCE_ADVICE,
        "symptoms_reviewed": [SYMPTOMS[s]["label"] for s in selected],
        "meta": {
            "age_group": age_group or "not specified",
            "sex": sex or "not specified",
            "duration": duration or "not specified",
        },
        "created_at": None,  # filled by the route when persisted
    }


def _confidence_bucket(match: float) -> str:
    """Map a 0-1 match ratio to a confidence label."""
    if match >= 0.70:
        return "High"
    if match >= 0.45:
        return "Moderate"
    return "Low"


def _matched_weight(condition_id: str, selected: list[str]) -> int:
    """Total symptom weight matched for tie-breaking."""
    cond = CONDITIONS[condition_id]
    return sum(w for s, w in cond["symptoms"].items() if s in selected)
