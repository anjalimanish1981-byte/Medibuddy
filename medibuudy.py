import streamlit as st
import datetime
from supabase import create_client
from streamlit_mic_recorder import speech_to_text
from groq import Groq

# ---------------------------------------------------------
# PAGE CONFIGURATION (Accessible Large Font Theme)
# ---------------------------------------------------------
st.set_page_config(page_title="MediBuddy - Friendly Health Companion", page_icon="💊", layout="centered")

# Custom CSS for high-visibility UI for elderly users
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-size: 18px !important;
        }
        .stButton button {
            font-size: 20px !important;
            padding: 10px 24px !important;
            border-radius: 12px !important;
        }
        .stTextInput input {
            font-size: 18px !important;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# KEYS & CLIENT INITIALIZATION
# ---------------------------------------------------------
SUPABASE_URL = "https://wecsfbazfodlypiybymb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndlY3NmYmF6Zm9kbHlwaXlieW1iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4MTYyOTksImV4cCI6MjEwMDM5MjI5OX0.dHkQR-3EDtIBRzhv0FT7cXBXv26ZG3IfV7ip2GjFcYk"
GROQ_API_KEY = "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"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

# Helper functions for database
def load_medications(user_id):
    try:
        res = supabase.table("medications").select("*").eq("user_id", user_id).order("id", desc=False).execute()
        return res.data if res.data else []
    except Exception:
        return []

def add_medication(user_id, name, dosage, time_str):
    try:
        supabase.table("medications").insert({
            "user_id": str(user_id),
            "med_name": name,
            "dosage": dosage,
            "time_to_take": time_str,
            "taken": False
        }).execute()
    except Exception:
        pass

def toggle_med_status(med_id, current_status):
    try:
        supabase.table("medications").update({"taken": not current_status}).eq("id", med_id).execute()
    except Exception:
        pass

# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------
if "user" not in st.session_state:
    st.title("💊 Welcome to MediBuddy")
    st.subheader("Your Friendly Health & Medicine Companion")
    
    display_name = st.text_input("Enter Your Name:")
    email = st.text_input("Enter Your Email Address:")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Send Login Code 📩", use_container_width=True):
            if email and display_name:
                try:
                    res = supabase.auth.sign_in_with_otp({
                        "email": email,
                        "options": {"data": {"full_name": display_name}}
                    })
                    st.success("Code sent! Please check your email inbox.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill in both your name and email.")

    otp_code = st.text_input("Enter the 6-digit code received in email:", type="password")

    if st.button("Sign In 🚀", use_container_width=True):
        if email and otp_code:
            try:
                res = supabase.auth.verify_otp({"email": email, "token": otp_code, "type": "email"})
                st.session_state.user = res.user
                st.session_state.user_name = display_name
                st.success("Welcome aboard!")
                st.rerun()
            except Exception:
                st.error("Invalid or expired code. Please try again.")

# ---------------------------------------------------------
# MAIN APP (LOGGED IN)
# ---------------------------------------------------------
else:
    user_email = st.session_state.user.email
    user_name = st.session_state.get('user_name', 'Friend')

    st.title("💊 MediBuddy")
    st.write(f"### 👋 Hello, **{user_name}**!")
    
    col_out, _ = st.columns([1, 3])
    with col_out:
        if st.button("Sign Out 🚪"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    st.divider()

    # Create Tabs for Reminder Dashboard and Health Chatbot
    tab_reminders, tab_chat = st.tabs(["⏰ Medicine Schedule", "💬 Ask Health Questions"])

    # ---------------------------------------------------------
    # TAB 1: MEDICINE REMINDERS & TRACKER
    # ---------------------------------------------------------
    with tab_reminders:
        st.subheader("📋 Your Today's Medicines")

        meds = load_medications(st.session_state.user.id)

        if meds:
            for med in meds:
                col_info, col_btn = st.columns([3, 1])
                status_emoji = "✅ Taken" if med["taken"] else "⏳ Pending"
                
                with col_info:
                    st.markdown(f"**{med['med_name']}** ({med['dosage']}) — *Take at {med['time_to_take']}*")
                    st.caption(f"Status: {status_emoji}")

                with col_btn:
                    btn_label = "Undo" if med["taken"] else "Mark Taken"
                    if st.button(btn_label, key=f"med_{med['id']}"):
                        toggle_med_status(med["id"], med["taken"])
                        st.rerun()
                st.divider()
        else:
            st.info("No medicines added yet. Use the form below to set up your schedule!")

        # Add New Medication Form
        with st.expander("➕ Add a New Medicine Schedule"):
            with st.form("add_med_form", clear_on_submit=True):
                med_name = st.text_input("Medicine Name:", placeholder="e.g., Paracetamol, Aspirin")
                dosage = st.text_input("Dosage:", placeholder="e.g., 1 tablet, 5ml")
                time_to_take = st.time_input("Scheduled Time:", datetime.time(8, 0))
                
                submitted = st.form_submit_button("Save Medicine 💾")
                if submitted:
                    if med_name and dosage:
                        formatted_time = time_to_take.strftime("%I:%M %p")
                        add_medication(st.session_state.user.id, med_name, dosage, formatted_time)
                        st.success(f"Added {med_name} for {formatted_time}!")
                        st.rerun()
                    else:
                        st.error("Please fill in all fields.")

    # ---------------------------------------------------------
    # TAB 2: SIMPLE HEALTH CHATBOT
    # ---------------------------------------------------------
    with tab_chat:
        st.subheader("💬 Ask MediBuddy Any Health Question")
        st.caption("MediBuddy gives simple, clear answers. *Note: Always consult your doctor for medical decisions.*")

        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant", 
                "content": f"Hello {user_name}! I am MediBuddy. You can ask me what a medicine does, why drink water, or how to stay healthy. How can I assist you today?"
            }]

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        st.write("🎙️ **Prefer Speaking?** Click below to speak:")
        spoken_text = speech_to_text(
            language='en',
            start_prompt="Click to Speak 🎙️",
            stop_prompt="Listening... (Click to Stop) 🛑",
            key='health_speech'
        )

        typed_prompt = st.chat_input("Type your health question here...")
        user_prompt = spoken_text if spoken_text else typed_prompt

        if user_prompt:
            st.chat_message("user").write(user_prompt)
            st.session_state.messages.append({"role": "user", "content": user_prompt})

            with st.chat_message("assistant"):
                try:
                    # Specialized prompt for elderly guidance
                    system_prompt = (
                        f"You are MediBuddy, a warm, patient, and friendly health assistant for elderly people speaking with {user_name}. "
                        f"Rules for your response:\n"
                        f"1. Explain health concepts, medicines, or symptoms in extremely simple, non-technical words.\n"
                        f"2. Keep answers short, clear, and reassuring.\n"
                        f"3. Always include a gentle reminder to consult their doctor or family before changing any medication."
                    )

                    response = groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model="llama-3.3-70b-versatile"
                    )
                    bot_reply = response.choices[0].message.content
                except Exception as e:
                    bot_reply = f"I am having trouble answering right now. Please check back shortly or consult your doctor."

                st.write(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
