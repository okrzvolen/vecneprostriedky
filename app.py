import os
import pandas as pd
import pdfplumber
from flask import Flask, render_template, request, send_file, io
import re

app = Flask(__name__)

# Zoznam okresov
OKRESY = [
    "Banská Bystrica", "Banská Štiavnica", "Brezno", "Detva", "Krupina", 
    "Lučenec", "Poltár", "Revúca", "Rimavská Sobota", "Veľký Krtíš", 
    "Zvolen", "Žarnovica", "Žiar nad Hronom"
]

def fix_broken_text(text):
    """Agresívne spájanie koncoviek pre stĺpec ULICA"""
    if not text: return ""
    words = text.split()
    if len(words) <= 1: return text
    
    result = [words[0]]
    for i in range(1, len(words)):
        # Ak má slovo 1-2 znaky a predchádzajúce je dlhé, spojíme ich
        if len(words[i]) <= 2 and len(words[i-1]) > 3:
            result[-1] = result[-1] + words[i]
        else:
            result.append(words[i])
    return " ".join(result)

def clean_text_standard(text):
    if not text: return ""
    t = str(text).replace('\n', ' ').replace('\r', '')
    t = re.sub(r'\s+', ' ', t) # Odstránenie viacnásobných medzier
    return t.strip()

def is_garbage(text):
    blacklist = ["číslo spisu", "záznamu", "dátum prijatia", "Okres:", "kópia"]
    return any(item.lower() in str(text).lower() for item in blacklist)

@app.route('/')
def index():
    return render_template('index.html', okresy=OKRESY)

@app.route('/convert', methods=['POST'])
def convert():
    selected_okres = request.form.get('okres')
    pdf_file = request.files['pdf']
    
    if not pdf_file:
        return "Nenahrali ste súbor", 400

    data = []
    headers = ["P.Č.", "DODÁVATEĽ", "ULICA", "Č. POPISNÉ", "MESTO (OBEC)", "OKRES", "IČO", 
               "DRUH KAROSÉRIE", "TOVÁRENSKÁ ZNAČKA", "TYP", "EČV", "STATUS", 
               "MIESTO DODANIA", "POZNÁMKA", "PČRD", "ÚTVAR"]

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Filtrovanie riadkov (musí byť P.Č. a nesmie byť garbage)
                    p_c = clean_text_standard(row[0])
                    full_row_text = " ".join([str(x) for x in row])
                    
                    if p_c and not is_garbage(full_row_text) and len(p_c) < 6:
                        # Príprava riadku presne podľa VBA mapovania
                        # row[0]=PČ, row[1]=Dodávateľ, row[3]=Mesto, row[4]=Ulica, row[5]=Č.Popisné...
                        ico = clean_text_standard(row[5]) if len(row) > 5 else ""
                        if not ico and len(row) > 6: ico = clean_text_standard(row[6])
                        
                        # Formátovanie IČO (pridanie núl)
                        if ico and len(ico) < 7:
                            ico = "00" + ico

                        new_row = [
                            p_c,                                    # P.Č.
                            clean_text_standard(row[1]),            # DODÁVATEĽ
                            fix_broken_text(clean_text_standard(row[3])), # ULICA (špeciálne čistenie)
                            clean_text_standard(row[4]),            # Č. POPISNÉ
                            clean_text_standard(row[2]),            # MESTO
                            selected_okres,                         # OKRES
                            ico,                                    # IČO
                            clean_text_standard(row[7]) if len(row)>7 else "", # KAROSERIA
                            clean_text_standard(row[8]) if len(row)>8 else "", # ZNACKA
                            clean_text_standard(row[9]) if len(row)>9 else "", # TYP
                            clean_text_standard(row[10]) if len(row)>10 else "", # ECV
                            "vybrané",                              # STATUS
                            clean_text_standard(row[12]) if len(row)>12 else "", # MIESTO DODANIA
                            "",                                     # POZNAMKA
                            "",                                     # PCRD
                            clean_text_standard(row[11]) if len(row)>11 else ""  # UTVAR
                        ]
                        data.append(new_row)

    df = pd.DataFrame(data, columns=headers)
    
    # Export do Excelu do pamäte (In-memory buffer)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_Export')
        # Formátovanie textu a tučné hlavičky sa dajú doplniť cez openpyxl
    
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Export_Dat.xlsx")

if __name__ == '__main__':
    app.run(debug=True)