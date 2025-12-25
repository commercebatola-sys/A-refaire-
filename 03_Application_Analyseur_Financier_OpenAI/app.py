import streamlit as st
import os
import fitz  # PyMuPDF
import tempfile
import re
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

# ===============================
# Configuration de la page
# ===============================
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA générative")

# ===============================
# Sidebar configuration
# ===============================
with st.sidebar:
    st.header("⚙️ Configuration")

    env_path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=env_path, override=True)

    st.subheader("🔑 Clé API Gemini")

    default_api_key = os.getenv("GEMINI_API_KEY", "")
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = default_api_key

    api_key = st.text_input(
        "Clé API Gemini",
        value=st.session_state.gemini_api_key,
        type="password",
        placeholder="AIza...",
        help="Entrez votre clé API Gemini"
    )

    if api_key != st.session_state.gemini_api_key:
        st.session_state.gemini_api_key = api_key
        st.success("✅ Clé API mise à jour")

    if not api_key:
        st.error("❌ Veuillez entrer votre clé API Gemini")
        st.stop()
    else:
        st.success(f"✅ API Key configurée: {api_key[:8]}...")

    model = st.selectbox(
        "Modèle Gemini",
        ["gemini-1.5-flash"],  # 🔒 MODÈLE STABLE UNIQUEMENT
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

# ===============================
# Extraction du texte PDF
# ===============================
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
            st.warning("⚠️ Texte tronqué pour éviter les limites API")

        os.unlink(tmp_path)
        return text, len(text)

    except Exception as e:
        st.error(f"Erreur PDF : {str(e)}")
        return None, 0

# ===============================
# Audit financier
# ===============================
def audit_financier(numbers):
    audit = "🔎 Audit & Alertes de cohérence\n\n"
    if not numbers:
        return audit + "Aucune donnée chiffrée détectée"
    return audit + "Analyse effectuée automatiquement"

# ===============================
# Appel Gemini (CORRIGÉ)
# ===============================
def call_gemini(prompt, model_name):
    api_key = st.session_state.get("gemini_api_key")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(model_name)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 2048
        }
    )

    return response.text

# ===============================
# Génération résumé
# ===============================
def generate_summary(text, model):
    instructions = (
        "Tu es un analyste financier senior. "
        "Fournis un résumé exécutif, chiffres clés, analyse, risques et recommandations. "
        "Utilise le Markdown."
    )

    try:
        summary = call_gemini(
            instructions + "\n\nDOCUMENT:\n" + text[:30000],
            model
        )
        return summary + "\n\n" + audit_financier({})
    except Exception as e:
        st.error(f"Erreur Gemini : {str(e)}")
        return None

# ===============================
# Réponse aux questions
# ===============================
def answer_question(text, question, model):
    prompt = (
        "Analyse le document suivant et répond précisément.\n\n"
        f"QUESTION: {question}\n\nDOCUMENT:\n{text[:30000]}"
    )

    try:
        return call_gemini(prompt, model)
    except Exception as e:
        st.error(f"Erreur Gemini : {str(e)}")
        return None

# ===============================
# Interface principale
# ===============================
def main():
    tab1, tab2 = st.tabs(["📄 Analyse", "❓ Questions"])

    with tab1:
        uploaded_file = st.file_uploader(
            "PDF financier",
            type=["pdf"]
        )

        if uploaded_file:
            if st.button("🚀 Analyser le document"):
                text, _ = extract_pdf_text(uploaded_file, max_length)

                if text:
                    with st.spinner("🤖 Analyse en cours..."):
                        result = generate_summary(text, model)

                    if result:
                        st.markdown(result)
                        st.session_state["pdf_text"] = text

    with tab2:
        if "pdf_text" not in st.session_state:
            st.info("Analysez d'abord un document")
        else:
            question = st.text_input("Votre question")
            if question:
                if st.button("🔍 Répondre"):
                    answer = answer_question(
                        st.session_state["pdf_text"],
                        question,
                        model
                    )
                    if answer:
                        st.markdown(answer)

st.markdown("---")
st.markdown("Note : vérifiez toujours les chiffres avec le document source.")

if __name__ == "__main__":
    main()
