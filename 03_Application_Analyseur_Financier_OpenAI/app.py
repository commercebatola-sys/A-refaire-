import streamlit as st
import os
import fitz  # PyMuPDF
import tempfile
import re
import google.generativeai as genai

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
# API KEY & Configuration Sidebar
# -----------------------------

GEMINI_API_KEY = "AIzaSyCvWyvjP_cRS-mVb6N_BJ3XKGdIqXSDB3A"
st.session_state["gemini_api_key"] = GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("🔑 Clé API configurée automatiquement")
    st.success(f"✅ API Key active : {GEMINI_API_KEY[:8]}...")

    model = st.selectbox(
        "Choisissez le modèle Gemini",
        [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro"
        ],
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
            page_text = page.get_text()
            text += f"\n\n=== [PAGE {i}] ===\n" + page_text.strip()

        text = "\n".join(line.strip() for line in text.splitlines())

        if len(text) > max_length:
            text = text[:max_length]
            st.warning(f"⚠️ Texte tronqué à {max_length} caractères")

        os.unlink(tmp_path)
        return text, len(text)

    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture du PDF : {str(e)}")
        return None, 0


def extract_numbers(text):
    numbers = {
        "CA": [],
        "Résultat net": [],
        "Marge": [],
        "Dette": [],
        "Trésorerie": []
    }

    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)

    for page_num, page_text in pages:
        for key in numbers.keys():
            pattern = rf"{key}[:\s]*([\d\s,.]+(?:M|k|K)?)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                value = match.replace(" ", "").replace(",", ".")
                numbers[key].append((value, page_num))

    return numbers


def audit_financier(numbers):
    audit_text = "🔎 **Audit & Alertes de cohérence**\n\n"
    issues = []

    ca_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["CA"] if re.sub(r"[^\d.]", "", val)]
    rn_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["Résultat net"] if re.sub(r"[^\d.]", "", val)]

    if ca_list and rn_list:
        if ca_list[-1] > ca_list[0] and rn_list[-1] < rn_list[0]:
            issues.append("⚠️ CA en hausse mais Résultat net en baisse")

    if numbers["Marge"]:
        issues.append(f"🔵 Marge identifiée : {numbers['Marge'][-1][0]}%")

    if numbers["Dette"] and numbers["Trésorerie"]:
        issues.append(
            f"⚠️ Dette = {numbers['Dette'][-1][0]} | Trésorerie = {numbers['Trésorerie'][-1][0]}"
        )

    if not issues:
        audit_text += "✅ Cohérence globale : satisfaisante"
    else:
        audit_text += "\n".join(issues)
        audit_text += "\n\n✅ Cohérence globale : moyenne"

    return audit_text


def generate_summary(text, model):
    instructions = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Lis ce document financier et fournis : résumé exécutif, tableau des chiffres clés, analyse des performances, "
        "structure financière, risques et guidance. "
        "Si l'information est absente, indique 'non précisé'. "
        "Sépare les sections Markdown : 🟢 Données factuelles, 🔵 Analyse & interprétation IA, 🟣 Recommandations."
    )

    try:
        gemini_model = genai.GenerativeModel(model)

        response = gemini_model.generate_content(
            instructions + "\n\nDOCUMENT :\n" + text[:30000]
        )

        summary = response.text
        numbers = extract_numbers(text)
        audit = audit_financier(numbers)

        return summary + "\n\n" + audit

    except Exception as e:
        st.error(f"❌ Erreur Gemini : {str(e)}")
        return None


def answer_question(text, question, model):
    instructions = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Ne jamais inventer de données. Cite les pages si possible. "
        "Réponds clairement avec : 🟢 Faits PDF, 🔵 Analyse IA, 🟣 Recommandations."
    )

    try:
        gemini_model = genai.GenerativeModel(model)

        prompt = (
            instructions +
            f"\n\nQUESTION : {question}\n\nTEXTE PDF :\n{text[:30000]}"
        )

        response = gemini_model.generate_content(prompt)
        answer = response.text

        if any(word in question.lower() for word in ["performance", "rentabilité", "évolution", "risques", "solidité"]):
            numbers = extract_numbers(text)
            audit = audit_financier(numbers)
            return answer + "\n\n" + audit

        return answer

    except Exception as e:
        st.error(f"❌ Erreur Gemini : {str(e)}")
        return None

# -----------------------------
# INTERFACE PRINCIPALE
# -----------------------------

def main():
    tab1, tab2 = st.tabs(["📄 Upload & Analyse", "❓ Questions"])

    with tab1:
        uploaded_file = st.file_uploader("Choisissez votre document financier (PDF)", type=["pdf"])

        if uploaded_file:
            if st.button("🚀 Analyser le document"):
                text, _ = extract_pdf_text(uploaded_file, max_length)

                if text:
                    summary = generate_summary(text, model)
                    if summary:
                        st.markdown(summary)
                        st.session_state["pdf_text"] = text

    with tab2:
        if "pdf_text" not in st.session_state:
            st.info("Analysez d'abord un document.")
        else:
            question = st.text_input("Posez votre question :")
            if st.button("🔍 Rechercher"):
                answer = answer_question(st.session_state["pdf_text"], question, model)
                if answer:
                    st.markdown(answer)


if __name__ == "__main__":
    main()
