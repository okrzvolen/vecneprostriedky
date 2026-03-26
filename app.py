import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# Nastavenie stránky
st.set_page_config(page_title="PDF Konvertor", layout="centered")

# CSS pre minimalistický štýl (podobný tomu, čo sme chceli)
st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #1d8045; color: white; border-radius: 8px; }
    .stSelectbox { margin-bottom: 20px; }
    </style>
    """, unsafe_allow_stdio=True)

def fix_broken_text(text):
    if not text: return ""
    words = text.strip().split()
    if len(words) <= 1: return text
    result = [words[0]]
    for i in range(1, len(words)):
        curr, prev = words[i], result[-1]
        is_category = bool(re.match(r'^[A-Z][0-9]$|^[0-9]$|^[GNO]$', curr))
        is_suffix = curr.lower() in ["nské", "ov", "ová", "ého", "om", "ých"] or curr[0].islower()
        if (len(curr) <= 4 and not is_category and is_suffix) or (len(curr) <= 2 and not is_category):
            result[-1] = result[-1] + curr
        else:
            result.append(curr)
    return " ".join(result)

st.title("KONVERZIA PDF DOKUMENTU DO EXCELU PRE VECNÉ PROSTRIEDKY")

okresy = ["Banská Bystrica", "Brezno", "Zvolen", "Detva", "Žiar nad Hronom", "Banská Štiavnica", "Žarnovica", "Krupina", "Lučenec", "Poltár", "Revúca", "Rimavská Sobota", "Veľký Krtíš"]
selected_okres = st.selectbox("Vyberte Okresný úrad", okresy)

uploaded_file = st.file_uploader("Nahrajte PDF súbor", type="pdf")

if uploaded_file is not None:
    if st.button("Konvertuj PDF"):
        data = []
        headers = ["P.Č.", "DODÁVATEĽ", "ULICA", "Č. POPISNÉ", "MESTO (OBEC)", "OKRES", "IČO", "DRUH KAROSÉRIE", "TOVÁRENSKÁ ZNAČKA", "TYP", "EČV", "STATUS", "MIESTO DODANIA", "POZNÁMKA", "PČRD", "ÚTVAR"]
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 5: continue
                        p_c = str(row[0]).strip()
                        if p_c.isdigit() and len(p_c) < 6:
                            # IČO čistenie
                            ico = str(row[5] if len(row) > 5 else "").replace(" ", "")
                            if not ico and len(row) > 6: ico = str(row[6]).replace(" ", "")
                            if ico.isdigit() and len(ico) < 8: ico = ico.zfill(8)

                            # Karoséria čistenie
                            kar_raw = str(row[7] if len(row) > 7 else "")
                            kar_fix = re.sub(r'([a-záäčďéíĺľňóôŕšťúýž])([A-Z][0-9])', r'\1 \2', kar_raw)

                            new_row = [
                                p_c, str(row[1]), fix_broken_text(str(row[3])), str(row[4]), str(row[2]),
                                selected_okres, ico, fix_broken_text(kar_fix),
                                str(row[8] if len(row)>8 else ""), str(row[9] if len(row)>9 else ""),
                                str(row[10] if len(row)>10 else "").replace(" ", ""),
                                "vybrané", fix_broken_text(str(row[12] if len(row)>12 else "")),
                                "", "", str(row[11] if len(row)>11 else "")
                            ]
                            data.append(new_row)

        if data:
            df = pd.DataFrame(data, columns=headers)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.success("✓ Databáza bola úspešne spracovaná.")
            st.download_button(
                label="Stiahnuť Excel",
                data=output.getvalue(),
                file_name="Export_Dat.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("V PDF sa nenašli žiadne dáta.")
