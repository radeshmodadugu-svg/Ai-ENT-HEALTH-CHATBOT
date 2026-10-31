from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from typing import List, Optional

import tensorflow as tf
import joblib
import numpy as np
import pandas as pd

import os
import sqlite3
import json
import uuid

from groq import Groq
from dotenv import load_dotenv

from followup_engine import get_best_followup
from followup_questions import FOLLOWUP_QUESTIONS

from red_flags import (
    check_red_flags,
    RED_FLAG_MESSAGE
)

from uncertainty import (
    classify_confidence
)

from explainability import (
    get_feature_contributions
)

from personalized_guidance import (
    get_personalized_guidance
)

from what_if import (
    run_what_if_prediction
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            preview TEXT,
            history TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ai-ent-health-chatbot-4e6g.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOAD MODEL
# ============================================================

print(
    "Loading trained model and encoders..."
)


model = tf.keras.models.load_model(
    "ent_dl_model.keras"
)


feature_names = joblib.load(
    "ent_features.joblib"
)


label_encoder = joblib.load(
    "ent_label_encoder.joblib"
)


# ============================================================
# FEATURE LOOKUP
# ============================================================

# Create a fast lookup dictionary.
# This avoids repeatedly using feature_names.index().

feature_to_index = {
    feature.strip().lower(): index
    for index, feature in enumerate(feature_names)
}


# ============================================================
# MODEL CALIBRATION
# ============================================================

CALIBRATION_TEMPERATURE = float(
    joblib.load(
        "calibration_temperature.joblib"
    )
)


def calibrate_probabilities(probabilities):

    probabilities = np.asarray(
        probabilities,
        dtype=np.float64
    )

    probabilities = np.clip(
        probabilities,
        1e-7,
        1.0
    )

    probabilities = (
        probabilities
        / probabilities.sum(
            axis=1,
            keepdims=True
        )
    )

    logits = np.log(
        probabilities
    )

    calibrated_logits = (
        logits
        / CALIBRATION_TEMPERATURE
    )

    calibrated = (
        tf.nn.softmax(
            calibrated_logits,
            axis=1
        ).numpy()
    )

    return calibrated


# ============================================================
# GROQ
# ============================================================

load_dotenv()


groq_api_key = os.getenv(
    "GROQ_API_KEY"
)


if not groq_api_key:

    raise RuntimeError(
        "GROQ_API_KEY was not found in the .env file."
    )


groq_client = Groq(
    api_key=groq_api_key
)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class Message(BaseModel):

    role: str

    content: str

    prediction: Optional[str] = None

    confidence: Optional[str] = None

    symptoms: Optional[List[str]] = None

    followup_question: Optional[str] = None

    explanation: Optional[list] = None

    guidance: Optional[dict] = None


class ChatRequest(BaseModel):

    user_id: str

    session_id: Optional[str] = None

    history: List[Message]


# ============================================================
# GET ALL SESSIONS
# ============================================================

@app.get(
    "/api/sessions/{user_id}"
)
async def get_sessions(
    user_id: str
):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT session_id, preview
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY ROWID DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return {
        "sessions": [
            {
                "session_id": row[0],
                "preview": row[1]
            }
            for row in rows
        ]
    }


# ============================================================
# GET SINGLE SESSION
# ============================================================

@app.get(
    "/api/session/{session_id}"
)
async def get_session(
    session_id: str
):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT history
        FROM chat_sessions
        WHERE session_id = ?
        """,
        (session_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        return {
            "history":
                json.loads(row[0])
        }

    return {
        "history": []
    }


# ============================================================
# DELETE SINGLE SESSION
# ============================================================

@app.delete(
    "/api/session/{session_id}"
)
async def delete_session(
    session_id: str,
    user_id: str
):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    # --------------------------------------------------------
    # Check session ownership
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT user_id
        FROM chat_sessions
        WHERE session_id = ?
        """,
        (session_id,)
    )

    row = cursor.fetchone()

    if not row:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Chat session not found."
        )

    stored_user_id = row[0]

    if stored_user_id != user_id:

        conn.close()

        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this chat."
        )

    # --------------------------------------------------------
    # Delete session
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM chat_sessions
        WHERE session_id = ?
        AND user_id = ?
        """,
        (
            session_id,
            user_id
        )
    )

    conn.commit()

    deleted_rows = cursor.rowcount

    conn.close()

    if deleted_rows == 0:

        raise HTTPException(
            status_code=404,
            detail="Chat session could not be deleted."
        )

    return {
        "success": True,
        "message": "Chat deleted successfully."
    }


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post(
    "/api/chat"
)
async def chat_endpoint(
    req: ChatRequest
):

    # ========================================================
    # SESSION
    # ========================================================

    current_session_id = (

        req.session_id

        if req.session_id

        else str(
            uuid.uuid4()
        )
    )


    if not req.history:

        return {
            "session_id":
                current_session_id,

            "prediction":
                None,

            "confidence":
                None,

            "reply":
                "Please describe your symptoms.",

            "followup_question":
                None,

            "explanation":
                None,

            "guidance":
                None,

            "symptoms":
                []
        }


    preview = (

        req.history[0].content[:25]
        + "..."

        if len(
            req.history[0].content
        ) > 25

        else req.history[0].content
    )


    # ========================================================
    # USER TEXT
    # ========================================================

    # Keep the entire history for conversation purposes,
    # but DO NOT send the entire user history to the
    # symptom extractor.
    #
    # This prevents previous symptoms from contaminating
    # the current prediction.

    latest_user_text = (
        req.history[-1].content
    )


    # ========================================================
    # LANGUAGE DETECTION
    # ========================================================

    language = "English"


    if any(
        char in latest_user_text
        for char in
        "అఆఇఈఉఊఎఏఐఒఓకఖగఘచఛజఝటఠడఢతథదధనపఫబభమయరలవశషసహళ"
    ):

        language = "Telugu"


    elif any(
        char in latest_user_text
        for char in
        "அஆஇஈஉஊஎஏஐஒஓகஙசஜஞடணதநபமயரலவழளறன"
    ):

        language = "Tamil"


    elif any(
        char in latest_user_text
        for char in
        "अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    ):

        language = "Hindi"


    latest_user_message = (
        latest_user_text
        .lower()
        .strip()
    )


    # ========================================================
    # DEFAULT VALUES
    # ========================================================

    predicted_disease = ""

    confidence_str = ""

    has_symptoms = False

    followup_question = None

    top_contributions = []

    guidance = None


    # ========================================================
    # RAW RED FLAG CHECK
    # ========================================================

    red_flag_phrases = [

        "difficulty breathing",

        "trouble breathing",

        "cannot breathe",

        "can't breathe",

        "shortness of breath",

        "breathing difficulty",

        "difficulty swallowing",

        "unable to swallow",

        "throat feels tight",

        "severe throat swelling",

        "coughing up blood",

        "blood in sputum",

        "chest pain",

        "fainting",

        "loss of consciousness"
    ]


    detected_red_flags = [

        phrase

        for phrase in red_flag_phrases

        if phrase in latest_user_message
    ]


    if detected_red_flags:

        return {

            "session_id":
                current_session_id,

            "reply": (
                "You mentioned a symptom that may require prompt "
                "medical attention. Please seek medical evaluation, "
                "especially if your breathing is difficult, worsening, "
                "or you are unable to speak or swallow normally."
            ),

            "prediction":
                "Medical Attention Recommended",

            "confidence":
                None,

            "followup_question":
                None,

            "explanation":
                None,

            "guidance":
                None,

            "symptoms":
                []
        }


    # ========================================================
    # FIND PREVIOUS FOLLOW-UP QUESTION
    # ========================================================

    followup_answer_symptom = None

    previous_followup_question = None


    if (
        len(req.history) >= 2
        and req.history[-1].role == "user"
    ):

        previous_messages = (
            req.history[:-1]
        )


        for msg in reversed(
            previous_messages
        ):

            if (
                msg.role == "assistant"
                and msg.followup_question
            ):

                previous_followup_question = (
                    msg.followup_question.strip()
                )


                for (
                    symptom,
                    question_text
                ) in FOLLOWUP_QUESTIONS.items():

                    if (
                        question_text
                        .strip()
                        .lower()
                        ==
                        previous_followup_question
                        .lower()
                    ):

                        followup_answer_symptom = (
                            symptom
                        )

                break


    # ========================================================
    # GPT SYMPTOM EXTRACTION
    # ========================================================

    extractor_prompt = (

        "Extract ONLY symptoms that the user explicitly "
        "states or clearly describes. "

        "The user may communicate in English, Telugu, "
        "Tamil, or Hindi. Understand the user's language "
        "and map the reported symptoms to the standardized "
        "English feature names in the accepted feature list. "

        "Do NOT infer, assume, predict, or add symptoms "
        "that are not present in the user's latest message. "

        "For example, if the user says "
        "'sore throat and fever', do NOT add cough "
        "or nasal congestion. "

        f"Match symptoms strictly to this accepted "
        f"feature list: {feature_names}. "

        "Return ONLY a comma-separated list of exact "
        "English feature names from the accepted list. "

        "If there are no explicitly mentioned symptoms, "
        "return exactly 'NONE'."
    )


    # ========================================================
    # FOLLOW-UP ANSWER CONTEXT
    # ========================================================

    if followup_answer_symptom:

        extractor_prompt += (

            f"\nThe previous assistant asked a follow-up "
            f"question about '{followup_answer_symptom}'. "

            f"The user's latest answer is: "
            f"'{latest_user_text}'. "

            "If the answer clearly means YES, include "
            "that symptom. "

            "If the answer clearly means NO, do not "
            "include that symptom."
        )


    # ========================================================
    # IMPORTANT:
    # USE ONLY LATEST USER MESSAGE FOR EXTRACTION
    # ========================================================

    extractor_prompt += (

        f"\nLatest user message: "
        f"'{latest_user_text}'"
    )


    # ========================================================
    # GPT EXTRACTION
    # ========================================================

    extractor_res = (
        groq_client
        .chat
        .completions
        .create(

            messages=[

                {
                    "role":
                        "user",

                    "content":
                        extractor_prompt
                }
            ],

            model=
                "openai/gpt-oss-20b"
        )
    )


    extracted_content = (

        extractor_res
        .choices[0]
        .message
        .content
        .strip()
    )


    # ========================================================
    # CLEAN EXTRACTED SYMPTOMS
    # ========================================================

    extracted_symptoms = []


    if (
        extracted_content
        and
        extracted_content.upper()
        != "NONE"
    ):

        extracted_symptoms = [

            symptom
            .strip()
            .lower()

            for symptom
            in extracted_content.split(",")

            if symptom.strip()
        ]


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    extracted_symptoms = list(
        dict.fromkeys(
            extracted_symptoms
        )
    )


    # ========================================================
    # FOLLOW-UP YES / NO HANDLING
    # ========================================================

    if followup_answer_symptom:

        latest_answer = (
            latest_user_text
            .strip()
            .lower()
        )


        # ----------------------------------------------------
        # Negative answers
        # ----------------------------------------------------

        negative_starts = (

            latest_answer == "no"

            or latest_answer.startswith(
                "no "
            )

            or latest_answer.startswith(
                "no,"
            )

            or latest_answer.startswith(
                "nope"
            )

            or latest_answer.startswith(
                "not really"
            )

            or latest_answer.startswith(
                "i don't"
            )

            or latest_answer.startswith(
                "i do not"
            )

            or latest_answer.startswith(
                "இல்லை"
            )

            or latest_answer.startswith(
                "లేదు"
            )

            or latest_answer.startswith(
                "नहीं"
            )
        )


        # ----------------------------------------------------
        # Positive answers
        # ----------------------------------------------------

        positive_starts = (

            latest_answer == "yes"

            or latest_answer.startswith(
                "yes "
            )

            or latest_answer.startswith(
                "yes,"
            )

            or latest_answer.startswith(
                "yeah"
            )

            or latest_answer.startswith(
                "yep"
            )

            or latest_answer.startswith(
                "sure"
            )

            or latest_answer.startswith(
                "definitely"
            )

            or latest_answer.startswith(
                "i do"
            )

            or latest_answer.startswith(
                "it does"
            )

            or latest_answer.startswith(
                "ஆம்"
            )

            or latest_answer.startswith(
                "అవును"
            )

            or latest_answer.startswith(
                "हाँ"
            )

            or latest_answer.startswith(
                "हां"
            )
        )


        # ----------------------------------------------------
        # YES
        # ----------------------------------------------------

        if positive_starts:

            if (
                followup_answer_symptom
                not in extracted_symptoms
            ):

                extracted_symptoms.append(
                    followup_answer_symptom
                )


        # ----------------------------------------------------
        # NO
        # ----------------------------------------------------

        elif negative_starts:

            extracted_symptoms = [

                symptom

                for symptom
                in extracted_symptoms

                if (
                    symptom
                    !=
                    followup_answer_symptom
                )
            ]


    # ========================================================
    # CHECK WHETHER SYMPTOMS EXIST
    # ========================================================

    has_symptoms = (
        len(extracted_symptoms) > 0
    )


    # ========================================================
    # EXTRACTED RED FLAG CHECK
    # ========================================================

    if has_symptoms:

        red_flags = check_red_flags(
            extracted_symptoms
        )


        if red_flags:

            return {

                "session_id":
                    current_session_id,

                "reply":
                    RED_FLAG_MESSAGE,

                "prediction":
                    "Medical Attention Recommended",

                "confidence":
                    None,

                "followup_question":
                    None,

                "explanation":
                    None,

                "guidance":
                    None,

                "symptoms":
                    extracted_symptoms
            }


    # ========================================================
    # DEEP LEARNING PIPELINE
    # ========================================================

    if has_symptoms:

        # ====================================================
        # FEATURE VECTOR
        # ====================================================

        input_data = np.zeros(
            len(feature_names),
            dtype=np.float32
        )


        for symptom in extracted_symptoms:

            cleaned_symptom = (
                symptom
                .strip()
                .lower()
            )


            if cleaned_symptom in feature_to_index:

                index = (
                    feature_to_index[
                        cleaned_symptom
                    ]
                )

                input_data[index] = 1.0


        # ====================================================
        # ACTIVE FEATURES
        # ====================================================

        active_features = [

            feature_names[i]

            for i, value
            in enumerate(input_data)

            if value == 1.0
        ]


        active_indices = [

            i

            for i, value
            in enumerate(input_data)

            if value == 1.0
        ]


        print(
            "\nDetected symptoms:"
        )

        print(
            extracted_symptoms
        )


        print(
            "\nActive features:"
        )

        print(
            active_features
        )


        print(
            "\nActive feature indices:"
        )

        print(
            active_indices
        )


        print(
            "\nTotal feature count:"
        )

        print(
            len(feature_names)
        )


        # ====================================================
        # INPUT DATAFRAME
        # ====================================================

        input_df = pd.DataFrame(
            [input_data],
            columns=feature_names
        )


        # ====================================================
        # MODEL PREDICTION
        # ====================================================

        raw_predictions = (
            model.predict(
                input_df,
                verbose=0
            )
        )


        # ====================================================
        # CALIBRATION
        # ====================================================

        predictions = (
            calibrate_probabilities(
                raw_predictions
            )
        )


        # ====================================================
        # PREDICTED INDEX
        # ====================================================

        predicted_index = int(
            np.argmax(
                predictions[0]
            )
        )


        # ====================================================
        # DEBUG - INPUT
        # ====================================================

        print(
            "\n================ INPUT DEBUG ================"
        )


        print(
            "Extracted symptoms:"
        )

        print(
            extracted_symptoms
        )


        print(
            "\nActive features:"
        )

        print(
            active_features
        )


        print(
            "\nActive feature indices:"
        )

        print(
            active_indices
        )


        print(
            "\nTotal feature count:"
        )

        print(
            len(feature_names)
        )


        # ====================================================
        # DEBUG - RAW MODEL OUTPUT
        # ====================================================

        print(
            "\n================ RAW PREDICTIONS ================"
        )


        for i, probability in enumerate(
            raw_predictions[0]
        ):

            disease = (
                label_encoder
                .inverse_transform(
                    [i]
                )[0]
            )


            print(
                f"{i}: {disease} = "
                f"{probability * 100:.6f}%"
            )


        # ====================================================
        # DEBUG - CALIBRATED OUTPUT
        # ====================================================

        print(
            "\n================ CALIBRATED PREDICTIONS ================"
        )


        for i, probability in enumerate(
            predictions[0]
        ):

            disease = (
                label_encoder
                .inverse_transform(
                    [i]
                )[0]
            )


            print(
                f"{i}: {disease} = "
                f"{probability * 100:.6f}%"
            )


        # ====================================================
        # PREDICTED DISEASE
        # ====================================================

        predicted_disease = (
            label_encoder
            .inverse_transform(
                [predicted_index]
            )[0]
        )


        print(
            "\nPredicted index:"
        )

        print(
            predicted_index
        )


        print(
            "\nPredicted disease:"
        )

        print(
            predicted_disease
        )


        print(
            "\nLabel encoder classes:"
        )

        print(
            label_encoder.classes_
        )


        print(
            "====================================================\n"
        )


        # ====================================================
        # UNCERTAINTY
        # ====================================================

        confidence = float(
            np.max(
                predictions[0]
            )
        )


        confidence_percent = (
            confidence * 100
        )


        confidence_level = (
            classify_confidence(
                confidence
            )
        )


        confidence_str = (
            f"{confidence_percent:.2f}% "
            f"({confidence_level})"
        )


        # ====================================================
        # EXPLAINABLE AI
        # ====================================================

        contributions = (
            get_feature_contributions(

                model,

                input_data,

                feature_names
            )
        )


        top_contributions = (
            contributions[:3]
        )


        # ====================================================
        # ADAPTIVE FOLLOW-UP
        # ====================================================

        asked_questions = []


        for message in req.history:

            if message.role == "assistant":

                question = (
                    message.followup_question
                )


                if question:

                    asked_questions.append(
                        question
                    )


        followup_result = (
            get_best_followup(

                extracted_symptoms,

                asked_questions,

                language
            )
        )


        if followup_result:

            followup_question = (
                followup_result[
                    "question"
                ]
            )


        # ====================================================
        # PERSONALIZED GUIDANCE
        # ====================================================

        guidance = (
            get_personalized_guidance(

                predicted_disease,

                extracted_symptoms,

                language
            )
        )


    # ========================================================
    # CONTEXT-AWARE MEDICAL GUARDRAILS
    # ========================================================

    is_first_message = (
        len(req.history) == 1
    )


    if is_first_message:

        disclaimer_rule = (

            " You MUST end your response with exactly "
            "this bolded sentence: "
            "**Disclaimer: This is not professional "
            "medical advice.**"
        )


    else:

        disclaimer_rule = (

            " DO NOT include a medical disclaimer "
            "in this response."
        )


    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_content = (

        "You are a specialized ENT triage assistant. "

        "You can answer general questions about "
        "medical symptoms, ENT conditions, and "
        "general treatment information. "

        "You cannot prescribe medication. "

        "If the user asks about antibiotics, explain "
        "generally when they may be used and advise "
        "medical evaluation rather than prescribing them. "

        "If the user asks about unrelated non-medical "
        "topics, politely decline. "

        "Respond in the same language used by the user. "

        "The supported languages are English, Telugu, "
        "Tamil, and Hindi. "

        "If the user writes in Telugu, respond in Telugu. "

        "If the user writes in Tamil, respond in Tamil. "

        "If the user writes in Hindi, respond in Hindi. "

        "If the user writes in English, respond in English. "

        "Keep medical feature names internally standardized "
        "in English, but present the final conversational "
        "response in the user's language. "

        "Keep responses short and friendly, maximum "
        "3 sentences."

        f"{disclaimer_rule}"
    )


    # ========================================================
    # GROQ CONVERSATION
    # ========================================================

    groq_messages = [

        {
            "role":
                "system",

            "content":
                system_content
        }
    ]


    for msg in req.history[:-1]:

        role = (

            "assistant"

            if msg.role == "assistant"

            else "user"
        )


        groq_messages.append({

            "role":
                role,

            "content":
                msg.content
        })


    # ========================================================
    # CURRENT GPT PROMPT
    # ========================================================

    if has_symptoms:

        current_prompt = (

            f"The user just said: "
            f"'{latest_user_text}'. "

            f"The deep learning model predicted: "
            f"{predicted_disease} "
            f"with model score {confidence_str}. "

            "Address the user's specific question "
            "naturally. "

            "If they are simply reporting symptoms, "
            "provide brief supportive-care guidance. "

            "Do not claim that the prediction is a "
            "confirmed diagnosis."
        )


    else:

        current_prompt = (

            f"The user just said: "
            f"'{latest_user_text}'. "

            "Answer conversationally based on the "
            "chat history. "

            "No new symptoms were detected."
        )


    groq_messages.append({

        "role":
            "user",

        "content":
            current_prompt
    })


    # ========================================================
    # FINAL GPT RESPONSE
    # ========================================================

    chat_completion = (

        groq_client
        .chat
        .completions
        .create(

            messages=
                groq_messages,

            model=
                "openai/gpt-oss-20b"
        )
    )


    reply_content = (

        chat_completion
        .choices[0]
        .message
        .content
        .strip()
    )


    # ========================================================
    # SAVE SESSION HISTORY
    # ========================================================

    updated_history = [

        msg.model_dump()

        for msg in req.history
    ]


    updated_history.append({

        "role":
            "assistant",

        "content":
            reply_content,

        "prediction": (

            predicted_disease

            if has_symptoms

            else None
        ),

        "confidence": (

            confidence_str

            if has_symptoms

            else None
        ),

        "symptoms": (

            extracted_symptoms

            if has_symptoms

            else []
        ),

        "followup_question":
            followup_question,

        "explanation": (

            top_contributions

            if has_symptoms

            else None
        ),

        "guidance": (

            guidance

            if has_symptoms

            else None
        )
    })


    # ========================================================
    # SAVE DATABASE
    # ========================================================

    conn = sqlite3.connect(
        "chat_history.db"
    )


    cursor = conn.cursor()


    cursor.execute(

        """
        INSERT INTO chat_sessions
        (session_id, user_id, preview, history)
        VALUES (?, ?, ?, ?)

        ON CONFLICT(session_id)
        DO UPDATE SET
            history=excluded.history,
            preview=excluded.preview
        """,

        (

            current_session_id,

            req.user_id,

            preview,

            json.dumps(
                updated_history,
                ensure_ascii=False
            )
        )
    )


    conn.commit()

    conn.close()


    # ========================================================
    # FINAL API RESPONSE
    # ========================================================

    return {

        "session_id":
            current_session_id,

        "prediction": (

            predicted_disease

            if has_symptoms

            else None
        ),

        "confidence": (

            confidence_str

            if has_symptoms

            else None
        ),

        "reply":
            reply_content,

        "followup_question":
            followup_question,

        "explanation": (

            top_contributions

            if has_symptoms

            else None
        ),

        "guidance": (

            guidance

            if has_symptoms

            else None
        ),

        "symptoms": (

            extracted_symptoms

            if has_symptoms

            else []
        )
    }


# ============================================================
# PHASE 8 - WHAT-IF SYMPTOM SIMULATION
# ============================================================

class WhatIfRequest(BaseModel):

    current_symptoms: List[str]

    added_symptoms: Optional[List[str]] = None

    removed_symptoms: Optional[List[str]] = None


@app.post(
    "/api/what-if"
)
async def what_if_endpoint(
    req: WhatIfRequest
):

    result = run_what_if_prediction(

        model,

        feature_names,

        label_encoder,

        req.current_symptoms,

        req.added_symptoms,

        req.removed_symptoms,

        calibrate_probabilities
    )

    return result