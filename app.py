import streamlit as st
import easyocr
import re
from PIL import Image
import pandas as pd



    
    # Премахване на дубликати
    seen = set()
    unique_matches = []
    for match in name_matches:
        key = (match["term"], match["category"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(match)
    
    # Обединяване с Е-номерата
    for e_num in set(e_matches):
        if e_num not in [m["term"].upper() for m in unique_matches]:
            info = ingredient_info.get(e_num, {"category": "Неизвестна категория", "type": "e_number", "e_numbers": [e_num]})
            unique_matches.append({
                "term": e_num,
                "category": info["category"],
                "type": "e_number",
                "e_numbers": [e_num]
            })
    
    return unique_matches


# --- БАЗА ДАННИ С ВРЕДНИ СЪСТАВКИ (БЪЛГАРСКИ + АНГЛИЙСКИ + Е-НОМЕРА) ---
harmful_ingredients_db = {
    "Парабени (консерванти)": {
        "names_bg": ["метилпарабен", "етилпарабен", "пропилпарабен", "бутилпарабен", "изобутилпарабен"],
        "names_en": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben", "isobutylparaben"],
        "e_numbers": []
    },
    "Формалдехид и донори": {
        "names_bg": ["формалдехид", "дмдм хидантоин", "кватерниум-15"],
        "names_en": ["formaldehyde", "dmdm hydantoin", "quaternium-15"],
        "e_numbers": ["E240"]
    },
    "Сулфати (пянообразуватели)": {
        "names_bg": ["натриев лаурил сулфат", "натриев лаурет сулфат", "амониев лаурил сулфат"],
        "names_en": ["sodium lauryl sulfate", "sodium laureth sulfate", "ammonium lauryl sulfate"],
        "e_numbers": []
    },
    "Фталати": {
        "names_bg": ["фталат", "диетилфталат", "дибутилфталат"],
        "names_en": ["phthalate", "dep", "dbp"],
        "e_numbers": []
    },
    "Изкуствени подсладители": {
        "names_bg": ["аспартам", "захарин", "сукралоза", "ацесулфам к"],
        "names_en": ["aspartame", "saccharin", "sucralose", "acesulfame k"],
        "e_numbers": ["E951", "E954", "E955", "E950"]
    },
    "Вредни оцветители": {
        "names_bg": ["тартразин", "сончев залез жълто", "азорубин", "брилянтно синьо", "еритрозин"],
        "names_en": ["tartrazine", "sunset yellow", "azorubine", "brilliant blue", "erythrosine"],
        "e_numbers": ["E102", "E110", "E122", "E133", "E127"]
    },
    "Глутамат натрий (усилвател на вкуса)": {
        "names_bg": ["мононатриев глутамат", "глутаминова киселина"],
        "names_en": ["monosodium glutamate", "msg", "glutamic acid"],
        "e_numbers": ["E621"]
    },
    "Трансмазнини": {
        "names_bg": ["хидрогенизирано растително масло", "трансмазнини", "частично хидрогенизирано масло"],
        "names_en": ["hydrogenated vegetable oil", "trans fat", "partially hydrogenated oil"],
        "e_numbers": []
    },
    "Нитрати и нитрити": {
        "names_bg": ["натриев нитрат", "калиев нитрат", "натриев нитрит", "калиев нитрит"],
        "names_en": ["sodium nitrate", "potassium nitrate", "sodium nitrite", "potassium nitrite"],
        "e_numbers": ["E251", "E252", "E250", "E249"]
    },
    "Бензоати (консерванти)": {
        "names_bg": ["натриев бензоат", "бензоена киселина", "калиев бензоат"],
        "names_en": ["sodium benzoate", "benzoic acid", "potassium benzoate"],
        "e_numbers": ["E211", "E210", "E212"]
    },
    "Сорбати (консерванти)": {
        "names_bg": ["сорбинова киселина", "калиев сорбат", "калциев сорбат"],
        "names_en": ["sorbic acid", "potassium sorbate", "calcium sorbate"],
        "e_numbers": ["E200", "E202", "E203"]
    },
    "BHA и BHT (антиоксиданти)": {
        "names_bg": ["бутилхидроксианизол", "бутилхидрокситолуен"],
        "names_en": ["butylated hydroxyanisole", "butylated hydroxytoluene", "bha", "bht"],
        "e_numbers": ["E320", "E321"]
    },
    "Пропилен гликол": {
        "names_bg": ["пропилен гликол", "пропан-1,2-диол"],
        "names_en": ["propylene glycol", "propane-1,2-diol"],
        "e_numbers": ["E490"]
    },
    "Силикони": {
        "names_bg": ["диметикон", "циклометикон", "циклопентасилоксан"],
        "names_en": ["dimethicone", "cyclomethicone", "cyclopentasiloxane"],
        "e_numbers": []
    },
    "Минерални масла": {
        "names_bg": ["минерално масло", "парафинум ликвидум", "петролатум", "вазелин"],
        "names_en": ["mineral oil", "paraffinum liquidum", "petrolatum", "vaseline"],
        "e_numbers": ["E905a", "E905b"]
    },
    "Пестициди (остатъци)": {
        "names_bg": ["пестицид", "хлорпирифос", "глифозат"],
        "names_en": ["pesticide", "chlorpyrifos", "glyphosate"],
        "e_numbers": []
    }
}

# Създаваме сет за бързо търсене (всичко в малки букви)
harmful_search_set = set()
ingredient_info = {}  # {"име": {"категория": "...", "e_number": "..."}}

for category, data in harmful_ingredients_db.items():
    # Добавяне на български имена
    for name_bg in data["names_bg"]:
        name_lower = name_bg.lower()
        harmful_search_set.add(name_lower)
        ingredient_info[name_lower] = {
            "category": category,
            "type": "bg_name",
            "e_numbers": data["e_numbers"]
        }
    
    # Добавяне на английски имена
    for name_en in data["names_en"]:
        name_lower = name_en.lower()
        harmful_search_set.add(name_lower)
        ingredient_info[name_lower] = {
            "category": category,
            "type": "en_name",
            "e_numbers": data["e_numbers"]
        }
    
    # Добавяне на Е-номера
    for e_num in data["e_numbers"]:
        e_num_upper = e_num.upper()
        harmful_search_set.add(e_num_upper)
        ingredient_info[e_num_upper] = {
            "category": category,
            "type": "e_number",
            "e_numbers": [e_num]
        }

df_harmful = pd.DataFrame(search_data)

def detect_harmful_ingredients(text):
    """Открива вредни съставки в текст (български, английски, Е-номера)"""
    text_lower = text.lower()
    
    # Търсене на Е-номера (E###)
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    e_matches = [f"E{m[1:].upper()}" for m in e_matches]
    
    # Търсене на имена (български и английски)
    name_matches = []
    
    for harmful_term in harmful_search_set:
        if harmful_term in text_lower:
            info = ingredient_info[harmful_term]
            name_matches.append({
                "term": harmful_term,
                "category": info["category"],
                "type": info["type"],
                "e_numbers": info["e_numbers"]
            })

# --- STREAMLIT UI ---
st.set_page_config(page_title="Анализатор на вредни съставки + Е-номера", page_icon="🛡️")
st.title("🛡️ Анализатор на вредни съставки")
st.markdown("Разпознава **имена на вредни съставки** и **Е-номера**")

# Табове
tab1, tab2, tab3 = st.tabs(["📸 Анализ на етикет", "📚 Списък с вредни съставки", "➕ Добави нова"])

with tab1:
    uploaded_file = st.file_uploader("Качи снимка на етикет", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Качена снимка", use_column_width=True)
        
        if st.button("🔍 Анализирай"):
            with st.spinner("Разпознаване на текст..."):
                # Запазване временно
                with open("temp.jpg", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                reader = easyocr.Reader(['en', 'bg'])
                result = reader.readtext("temp.jpg", detail=0, paragraph=True)
                text = " ".join(result)
                text_lower = text.lower()
                
                # Търсене на Е-номера
                e_matches = re.findall(r'e[0-9]{3}', text_lower)
                e_matches = [f"E{m[1:].upper()}" for m in e_matches]
                
                # Търсене на имена
                name_matches = []
                for category, data in harmful_ingredients_db.items():
                    for name in data["names"]:
                        if name.lower() in text_lower:
                            name_matches.append({
                                "име": name.title(),
                                "категория": category,
                                "е-номер": ", ".join(data["e_numbers"]) if data["e_numbers"] else "-"
                            })
                
                # Резултати
                st.subheader("📝 Разпознат текст:")
                st.text(text[:500])
                
                st.subheader("🔬 Открити вредни съставки:")
                
                if name_matches or e_matches:
                    if name_matches:
                        st.error(f"⚠️ Открити {len(name_matches)} вредни съставки по име:")
                        for match in name_matches:
                            st.warning(f"**{match['име']}** → {match['категория']} (Е-номер: {match['е-номер']})")
                    
                    if e_matches:
                        st.error(f"⚠️ Открити {len(e_matches)} Е-номера:")
                        for e_num in set(e_matches):
                            # Намери категорията
                            category = "Неизвестен"
                            for cat, data in harmful_ingredients_db.items():
                                if e_num in data["e_numbers"]:
                                    category = cat
                                    break
                            st.warning(f"**{e_num}** → {category}")
                else:
                    st.success("✅ Не са открити вредни съставки или Е-номера")
                
                import os
                os.remove("temp.jpg")

with tab2:
    st.subheader("📋 Списък на вредните съставки и Е-номера")
    st.dataframe(df_harmful, use_container_width=True)
    
    st.download_button(
        label="📥 Изтегли като CSV",
        data=df_harmful.to_csv(index=False),
        file_name="harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("➕ Добавяне на нова вредна съставка")
    new_name = st.text_input("Име на съставката")
    new_category = st.text_input("Категория")
    new_e_number = st.text_input("Е-номер (напр. E999)", placeholder="E999")
    
    if st.button("Добави"):
        st.success(f"✅ Добавено: {new_name} → {new_category} (Е-номер: {new_e_number})")
        # Тук може да добавиш логика за запис във файл
