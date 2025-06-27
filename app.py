import streamlit as st
import pandas as pd
import json
import requests
import matplotlib.pyplot as plt

#setup openrouter, use st.secrets if hosted,cloud
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY")

# st.sidebar.text_input("Enter your OpenRouter API Key", type="password") ; demo

if not OPENROUTER_API_KEY:
    st.warning("Please enter your OpenRouter API key to proceed.")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://leadqualificationagent.streamlit.app",
    "X-Title": "LeadQualifierAI"
}
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-7b-instruct"

#todochangepromptaccto escalate and ignore
SYSTEM_PROMPT_BASE = """
You are a helpful AI assistant for a B2B sales team. Your goal is to classify and respond to incoming leads based on message content.

Rules:
1. If the message shows strong interest in buying (e.g. asking for pricing, demo, setup call), classify it as:
   - qualification: "High"
   - action: "Escalate"
   - reply: Write a highly professional, confident, impactful message (max 40 words).

2. If the message shows general interest or product curiosity, classify it as:
   - qualification: "Medium"
   - action: "Send reply"
   - reply: Write a concise and professional message (max 40 words).

3. If the message expresses disinterest, spam, or requests to unsubscribe, classify as:
   - qualification: "Low"
   - action: "Ignore"
   - reply: (Leave blank)

Constraints:
- Only output the JSON. No comments, markdown, or extra formatting.
- The reply field must only be filled if action is not "Ignore".
"""

USER_PROMPT_TEMPLATE = """
Lead Details:
Name: {name}
Email: {email}
Message: {message}

Return the output in this strict JSON format:
{{
    "qualification": "High" / "Medium" / "Low",
    "action": "Send reply" / "Ignore" / "Escalate",
    "reply": "<short professional reply only if action is not 'Ignore'>"
}}
"""

#fixlater
def process_lead(name, email, message, tone):
    prompt = USER_PROMPT_TEMPLATE.format(name=name, email=email, message=message)
    tone_instruction = f"\nReply tone preference: {tone}." if tone != "Default" else ""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_BASE + tone_instruction},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        res = requests.post(API_URL, headers=HEADERS, json=payload)
        raw = res.json()["choices"][0]["message"]["content"]
        json_data = json.loads(raw[raw.find('{'): raw.rfind('}') + 1])
        return {
            "Qualification": json_data.get("qualification", "Unknown"),
            "Action": json_data.get("action", "Unknown"),
            "AI Reply": json_data.get("reply", "")
        }
    except Exception as e:
        return {
            "Qualification": "Error",
            "Action": "Error",
            "AI Reply": f"❌ {str(e)}"
        }

def detect_spam(text):
    return any(word in text.lower() for word in ["unsubscribe", "stop emailing", "remove me"])

st.set_page_config(page_title="lead-qualification AI", layout="wide")
st.title("Lead Qualification AI Agent")

#add emojisin sidebar
st.sidebar.title("Filters")
st.sidebar.caption("by rohn.")

show_sample = st.radio("Show Sample Preview?", ["Yes", "No"], index=0)
file = st.file_uploader("Upload a CSV with Name, Email, Message", type="csv")

# reply tone dropdown
reply_tone = st.sidebar.selectbox("Reply Tone", ["Default", "Formal", "Friendly", "Empathetic"])

# pie chart toggle
show_pie = st.sidebar.checkbox("Show Pie Chart Summary", value=False)

# add demomode or session restbutton, session reset button for file upload
if file:
    if "previous_file" in st.session_state and file.name != st.session_state.previous_file:
        st.session_state.pop("result_df", None)
    st.session_state.previous_file = file.name

if file:
    df = pd.read_csv(file)
    if show_sample == "Yes":
        st.write("📄 Sample Preview:", df)

    if not {"Name", "Email", "Message"}.issubset(df.columns):
        st.error("CSV must contain Name, Email, and Message columns.")
        st.stop()

    if "result_df" not in st.session_state:
        with st.spinner("Processing leads..."):
            results = []
            bar = st.progress(0)
            for i, row in df.iterrows():
                res = process_lead(row["Name"], row["Email"], row["Message"], reply_tone)
                res.update({
                    "Name": row["Name"],
                    "Email": row["Email"],
                    "Message": row["Message"],
                    "Spam": "Yes" if detect_spam(row["Message"]) else "No",
                    "Summary": row["Message"][:50] + ("..." if len(row["Message"]) > 50 else "")
                })
                results.append(res)
                bar.progress((i + 1) / len(df))
            st.session_state.result_df = pd.DataFrame(results)

    df_result = st.session_state.result_df

    selected = st.sidebar.multiselect(
        "Filter by Lead Quality", ["High", "Medium", "Low"], default=["High", "Medium", "Low"]
    )
    filtered = df_result[df_result["Qualification"].isin(selected)]

    #add color in rows, dark mode light color
    st.subheader("📊 Summary")
    counts = df_result["Qualification"].value_counts()
    st.markdown(
        f"- 🟢 **High**: {counts.get('High', 0)}  \n"
        f"- 🟡 **Medium**: {counts.get('Medium', 0)}  \n"
        f"- 🔴 **Low**: {counts.get('Low', 0)}"
    )

    #
    st.subheader("📋 Filtered Leads")
    st.dataframe(filtered, use_container_width=True)

    for i, row in filtered.iterrows():
        if row["AI Reply"]:
            with st.expander(f"✉️ Reply to {row['Name']} ({row['Email']})"):
                st.code(row["AI Reply"], language="text")

    # todo:remove summarycolumn due to omission
    final_csv = df_result[["Name", "Email", "Message", "Qualification", "Action", "AI Reply", "Spam"]]
    st.download_button("⬇️ Download Results", final_csv.to_csv(index=False).encode("utf-8"), "qualified_leads.csv")

    # small pie chart below everything
    if show_pie:
        st.subheader("📈 Lead Qualification Breakdown (Pie Chart)")
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')
        st.pyplot(fig)

else:
    st.info("please upload a CSV to begin.")
