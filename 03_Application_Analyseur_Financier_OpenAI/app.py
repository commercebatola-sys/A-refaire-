import streamlit as st
import os
import fitz  # PyMuPDF
from dotenv import load_dotenv, find_dotenv
import tempfile
import re
import google.generativeai as genai

# -----------------------------
# CONFIGURATION DE LA PAGE
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
# SIDEBAR CONFIGURATION (API IDENTIQUE AU COMPORTEMENT OPENAI)
# -----------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    env_path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=env_path, override=True)

    st.subheader("🔑 Clé API Gemini")
    default_api_key = os.getenv("GEMINI_API_KEY", "")

    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = default_api_key

    api_key = st.text_input(
        "Clé API Gemini",
        value=st.session_state.openai_api_key,
        type="password",
        placeholder="AIza...",
        help="Entrez votre clé API Gemini. Elle sera sauvegardée pour cette session."
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
# EXTRACTION TEXTE PDF
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

# -----------------------------
# EXTRACTION DES CHIFFRES
# -----------------------------
def extract_numbers(text):
    numbers = {"CA": [], "Résultat net": [], "Marge": [], "Dette": [], "Trésorerie": []}
    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)

    for page_num, page_text in pages:
        for key in numbers:
            pattern = rf"{key}[:\s]*([\d\s,.]+(?:M|k|K)?)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                numbers[key].append((match.replace(" ", "").replace(",", "."), page_num))

    return numbers

# -----------------------------
# AUDIT FINANCIER
# -----------------------------
def audit_financier(numbers):
    audit = "🔎 **Audit & Alertes de cohérence**\n\n"
    issues = []

    ca = [float(re.sub(r"[^\d.]", "", v)) for v, _ in numbers["CA"] if re.sub(r"[^\d.]", "", v)]
    rn = [float(re.sub(r"[^\d.]", "", v)) for v, _ in numbers["Résultat net"] if re.sub(r"[^\d.]", "", v)]

    if ca and rn and ca[-1] > ca[0] and rn[-1] < rn[0]:
        issues.append("⚠️ CA en hausse mais Résultat net en baisse")

    if numbers["Marge"]:
        issues.append(f"🔵 Marge identifiée : {numbers['Marge'][-1][0]}%")

    if numbers["Dette"] and numbers["Trésorerie"]:
        issues.append(f"⚠️ Dette = {numbers['Dette'][-1][0]} | Trésorerie = {numbers['Trésorerie'][-1][0]}")

    audit += "\n".join(issues) if issues else "✅ Cohérence globale satisfaisante"
    return audit

# -----------------------------
# APPEL GEMINI (CORRECTION CRITIQUE)
# -----------------------------
def call_gemini(prompt, model_name):
    api_key = st.session_state.get("openai_api_key")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(f"models/{model_name}-001")
    response = model.generate_content(prompt)
    return response.text

# -----------------------------
# RÉSUMÉ
# -----------------------------
def generate_summary(text, model):
    instructions = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Fournis : résumé exécutif, chiffres clés, analyse, risques et recommandations. "
        "Sépare : 🟢 Données factuelles, 🔵 Analyse IA, 🟣 Recommandations."
    )

    summary = call_gemini(instructions + "\n\nDOCUMENT:\n" + text[:30000], model)
    audit = audit_financier(extract_numbers(text))
    return summary + "\n\n" + audit

# -----------------------------
# QUESTIONS
# -----------------------------
def answer_question(text, question, model):
    prompt = (
        "Ne jamais inventer. Cite les pages si possible.\n"
        f"QUESTION : {question}\n\nTEXTE:\n{text[:30000]}"
    )

    answer = call_gemini(prompt, model)

    if any(w in question.lower() for w in ["performance", "rentabilité", "risque", "solidité"]):
        answer += "\n\n" + audit_financier(extract_numbers(text))

    return answer

# -----------------------------
# INTERFACE
# -----------------------------
def main():
    tab1, tab2 = st.tabs(["📄 Analyse", "❓ Questions"])

    with tab1:
        pdf = st.file_uploader("PDF financier", type=["pdf"])
        if pdf and st.button("🚀 Analyser"):
            text, _ = extract_pdf_text(pdf, max_length)
            if text:
                result = generate_summary(text, model)
                st.markdown(result)
                st.session_state["pdf_text"] = text

    with tab2:
        if "pdf_text" not in st.session_state:
            st.info("Analysez d'abord un PDF")
        else:
            q = st.text_input("Votre question")
            if st.button("🔍"):
                st.markdown(answer_question(st.session_state["pdf_text"], q, model))

if __name__ == "__main__":
    main()
