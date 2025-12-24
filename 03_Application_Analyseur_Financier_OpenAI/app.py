import streamlit as st
import os
import fitz  # PyMuPDF
from dotenv import load_dotenv, find_dotenv
import tempfile
import re
import google.generativeai as genai

# Configuration de la page
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA générative")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    env_path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=env_path, override=True)

    st.subheader("🔑 Clé API Gemini")
    default_api_key = os.getenv("GEMINI_API_KEY", "")
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = default_api_key

    api_key = st.text_input(
        "Clé API Gemini",
        value=st.session_state.openai_api_key,
        type="password",
        placeholder="AIza...",
        help="Entrez votre clé API Gemini"
    )

    if api_key != st.session_state.openai_api_key:
        st.session_state.openai_api_key = api_key
        st.success("✅ Clé API mise à jour !")

    if not api_key:
        st.error("❌ Veuillez entrer votre clé API Gemini")
        st.stop()
    else:
        st.success(f"✅ API Key configurée: {api_key[:8]}...")

    model = st.selectbox(
        "Modèle Gemini",
        ["gemini-1.5-flash", "gemini-1.5-pro"],
        index=0
    )

    max_length = st.slider("Longueur maximale du texte (caractères)", 50000, 200000, 120000, step=10000)


# --- Extraction du texte PDF ---
def extract_pdf_text(pdf_file, max_length=120000):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name

        pdf = fitz.open(tmp_path)
        text = ""
        for i, page in enumerate(pdf, start=1):
            text += f"\n\n=== [PAGE {i}] ===\n{page.get_text().strip()}"

        text = "\n".join(line.strip() for line in text.splitlines())
        if len(text) > max_length:
            text = text[:max_length]
            st.warning("⚠️ Texte tronqué")

        os.unlink(tmp_path)
        return text, len(text)
    except Exception as e:
        st.error(str(e))
        return None, 0


# --- Extraction chiffres ---
def extract_numbers(text):
    numbers = {"CA": [], "Résultat net": [], "Marge": [], "Dette": [], "Trésorerie": []}
    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)

    for page_num, page_text in pages:
        for key in numbers:
            pattern = rf"{key}[:\s]*([\d\s,.]+)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                numbers[key].append((match, page_num))
    return numbers


# --- Audit ---
def audit_financier(numbers):
    audit = "🔎 Audit & Alertes\n\n"
    if not numbers["CA"]:
        audit += "Aucune donnée suffisante.\n"
    else:
        audit += "Analyse basique effectuée.\n"
    return audit


# --- Appel Gemini ---
def call_gemini(prompt, model):
    api_key = st.session_state.get("openai_api_key")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model)
    response = model.generate_content(prompt)
    return response.text


# --- Résumé ---
def generate_summary(text, model):
    instructions = (
        "Tu es un analyste financier senior. "
        "Fournis : résumé exécutif, chiffres clés, analyse, risques et recommandations. "
        "Si absent : non précisé."
    )

    prompt = f"{instructions}\n\nDOCUMENT:\n{text}"
    summary = call_gemini(prompt, model)
    numbers = extract_numbers(text)
    audit = audit_financier(numbers)
    return summary + "\n\n" + audit


# --- Questions ---
def answer_question(text, question, model):
    prompt = (
        "Tu es analyste financier. "
        "Ne jamais inventer. Cite les pages si possible.\n\n"
        f"QUESTION : {question}\n\nDOCUMENT :\n{text}"
    )
    answer = call_gemini(prompt, model)
    return answer


# --- Interface ---
def main():
    tab1, tab2 = st.tabs(["📄 Analyse", "❓ Questions"])

    with tab1:
        uploaded_file = st.file_uploader("PDF", type=["pdf"])
        if uploaded_file and st.button("Analyser"):
            text, _ = extract_pdf_text(uploaded_file)
            summary = generate_summary(text, model)
            st.markdown(summary)
            st.session_state["pdf_text"] = text

    with tab2:
        if "pdf_text" in st.session_state:
            q = st.text_input("Votre question")
            if st.button("Répondre"):
                st.markdown(answer_question(st.session_state["pdf_text"], q, model))


if __name__ == "__main__":
    main()
