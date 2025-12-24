import streamlit as st
import os
import fitz  # PyMuPDF
import tempfile
import re
import requests
import json

# -----------------------------
# CONFIGURATION PAGE
# -----------------------------
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA générative")

# -----------------------------
# API KEY & CONFIGURATION
# -----------------------------
GEMINI_API_KEY = "AIzaSyCvWyvjP_cRS-mVb6N_BJ3XKGdIqXSDB3A"
st.session_state["gemini_api_key"] = GEMINI_API_KEY

with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("🔑 Clé API configurée automatiquement")
    st.success(f"✅ API Key active : {GEMINI_API_KEY[:8]}...")

    model = st.selectbox(
        "Choisissez le modèle Gemini",
        ["gemini-1.5-flash"],
        index=0
    )

    max_length = st.slider(
        "Longueur maximale du texte (caractères)",
        50000, 200000, 120000, step=10000
    )

    st.markdown("---")
    st.markdown("**Instructions :**")
    st.markdown("1. Uploadez votre PDF financier")
    st.markdown("2. Obtenez un résumé structuré avec audit")
    st.markdown("3. Posez des questions spécifiques")

# -----------------------------
# GEMINI REST CALL (CORRIGÉ)
# -----------------------------
def call_gemini(prompt, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")

    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

# -----------------------------
# FONCTIONS
# -----------------------------
def extract_pdf_text(pdf_file, max_length=120000):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name

        pdf = fitz.open(tmp_path)
        text = ""

        for i, page in enumerate(pdf, start=1):
            text += f"\n\n=== [PAGE {i}] ===\n" + page.get_text().strip()

        text = "\n".join(line.strip() for line in text.splitlines())

        if len(text) > max_length:
            text = text[:max_length]
            st.warning(f"⚠️ Texte tronqué à {max_length} caractères")

        os.unlink(tmp_path)
        return text, len(text)

    except Exception as e:
        st.error(f"❌ Erreur lecture PDF : {str(e)}")
        return None, 0


def extract_numbers(text):
    numbers = {"CA": [], "Résultat net": [], "Marge": [], "Dette": [], "Trésorerie": []}
    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)

    for page_num, page_text in pages:
        for key in numbers:
            pattern = rf"{key}[:\s]*([\d\s,.]+(?:M|k|K)?)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                numbers[key].append((match.replace(" ", "").replace(",", "."), page_num))

    return numbers


def audit_financier(numbers):
    audit = "🔎 **Audit & Alertes de cohérence**\n\n"
    issues = []

    if numbers["CA"] and numbers["Résultat net"]:
        try:
            ca_start = float(re.sub(r"[^\d.]", "", numbers["CA"][0][0]))
            ca_end = float(re.sub(r"[^\d.]", "", numbers["CA"][-1][0]))
            rn_start = float(re.sub(r"[^\d.]", "", numbers["Résultat net"][0][0]))
            rn_end = float(re.sub(r"[^\d.]", "", numbers["Résultat net"][-1][0]))

            if ca_end > ca_start and rn_end < rn_start:
                issues.append("⚠️ CA en hausse mais Résultat net en baisse")
        except:
            pass

    if numbers["Marge"]:
        issues.append(f"🔵 Marge identifiée : {numbers['Marge'][-1][0]}%")

    if numbers["Dette"] and numbers["Trésorerie"]:
        issues.append(f"⚠️ Dette = {numbers['Dette'][-1][0]} | Trésorerie = {numbers['Trésorerie'][-1][0]}")

    audit += "✅ Cohérence globale : satisfaisante" if not issues else "\n".join(issues)
    return audit


def generate_summary(text, model):
    prompt = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior.\n"
        "Fournis : résumé exécutif, chiffres clés, performance, structure financière, risques.\n"
        "Si absent : 'non précisé'.\n"
        "Sections : 🟢 Données factuelles | 🔵 Analyse IA | 🟣 Recommandations.\n\n"
        + text[:30000]
    )

    summary = call_gemini(prompt, model)
    audit = audit_financier(extract_numbers(text))
    return summary + "\n\n" + audit


def answer_question(text, question, model):
    prompt = (
        "Analyse ce document financier sans jamais inventer.\n"
        "Réponds avec : 🟢 Faits PDF | 🔵 Analyse IA | 🟣 Recommandations.\n\n"
        f"QUESTION : {question}\n\nDOCUMENT :\n{text[:30000]}"
    )

    answer = call_gemini(prompt, model)

    if any(w in question.lower() for w in ["performance", "rentabilité", "risques", "solidité"]):
        answer += "\n\n" + audit_financier(extract_numbers(text))

    return answer

# -----------------------------
# INTERFACE
# -----------------------------
def main():
    tab1, tab2 = st.tabs(["📄 Upload & Analyse", "❓ Questions"])

    with tab1:
        uploaded_file = st.file_uploader("Choisissez votre PDF", type=["pdf"])
        if uploaded_file and st.button("🚀 Analyser"):
            text, _ = extract_pdf_text(uploaded_file, max_length)
            if text:
                summary = generate_summary(text, model)
                st.markdown(summary)
                st.session_state["pdf_text"] = text

    with tab2:
        if "pdf_text" not in st.session_state:
            st.info("Analysez d'abord un document.")
        else:
            question = st.text_input("Votre question")
            if st.button("🔍 Rechercher"):
                st.markdown(answer_question(st.session_state["pdf_text"], question, model))


if __name__ == "__main__":
    main()
