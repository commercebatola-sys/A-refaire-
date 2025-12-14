import streamlit as st
import os
import fitz  # PyMuPDF
from openai import OpenAI
import tempfile
import re

# =======================
# 🔐 CLÉ API PRIVÉE
# =======================
_API_KEY = "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"


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

    # Injection silencieuse de la clé API (aucune interface)
    st.session_state.openai_api_key = _API_KEY

    model = st.selectbox(
        "Modèle OpenAI",
        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
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


# --- Extraction du texte PDF ---
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
        st.error(f"❌ Erreur PDF : {e}")
        return None, 0


# --- Extraction automatique des chiffres ---
def extract_numbers(text):
    numbers = {"CA": [], "Résultat net": [], "Marge": [], "Dette": [], "Trésorerie": []}
    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)

    for page_num, page_text in pages:
        for key in numbers:
            pattern = rf"{key}[:\s]*([\d\s,.]+(?:M|k|K)?)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                numbers[key].append((match.replace(" ", "").replace(",", "."), page_num))

    return numbers


# --- Audit financier ---
def audit_financier(numbers):
    audit = "🔎 Audit & Alertes de cohérence\n\n"
    issues = []

    ca = [float(re.sub(r"[^\d.]", "", v)) for v, _ in numbers["CA"] if re.sub(r"[^\d.]", "", v)]
    rn = [float(re.sub(r"[^\d.]", "", v)) for v, _ in numbers["Résultat net"] if re.sub(r"[^\d.]", "", v)]

    if ca and rn and ca[-1] > ca[0] and rn[-1] < rn[0]:
        issues.append("⚠️ CA en hausse mais résultat net en baisse")

    if numbers["Dette"] and numbers["Trésorerie"]:
        issues.append("⚠️ Dette et trésorerie évoluent en sens opposé")

    audit += "\n".join(issues) if issues else "✅ Cohérence globale satisfaisante"
    return audit


# --- Génération du résumé ---
def generate_summary(text, model):
    client = OpenAI(api_key=st.session_state.openai_api_key)

    instructions = (
        "Tu es analyste financier et auditeur senior. "
        "Sépare clairement : 🟢 Données factuelles, 🔵 Analyse IA, 🟣 Recommandations."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": text}
        ],
        max_tokens=2000,
        temperature=0.1
    )

    summary = response.choices[0].message.content
    audit = audit_financier(extract_numbers(text))
    return summary + "\n\n" + audit


# --- Questions ---
def answer_question(text, question, model):
    client = OpenAI(api_key=st.session_state.openai_api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Réponds avec faits, analyse et recommandations."},
            {"role": "user", "content": f"{question}\n\n{text}"}
        ],
        max_tokens=1000,
        temperature=0.1
    )

    answer = response.choices[0].message.content

    if any(k in question.lower() for k in ["performance", "rentabilité", "risque"]):
        answer += "\n\n" + audit_financier(extract_numbers(text))

    return answer


# --- Interface ---
def main():
    tab1, tab2 = st.tabs(["📄 Upload & Analyse", "❓ Questions"])

    with tab1:
        uploaded_file = st.file_uploader("PDF financier", type=["pdf"])
        if uploaded_file and st.button("🚀 Analyser"):
            text, _ = extract_pdf_text(uploaded_file)
            if text:
                summary = generate_summary(text, model)
                st.markdown(summary)
                st.session_state.pdf_text = text

    with tab2:
        if "pdf_text" in st.session_state:
            q = st.text_input("Votre question")
            if q and st.button("🔍 Répondre"):
                st.markdown(answer_question(st.session_state.pdf_text, q, model))


if __name__ == "__main__":
    main()
