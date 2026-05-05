import streamlit as st
import easyocr
import re
import pandas as pd
from PIL import Image
import os

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

import re

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

st.set_page_config(page_title="Анализатор на вредни съставки", page_icon="🛡️")
st.title("🛡️ Анализатор на вредни съставки")
st.markdown("Разпознава вредни съставки на **български**, **английски** и **Е-номера**")

# Странична лента с информация
with st.sidebar:
    st.header("ℹ️ Как работи")
    st.markdown("""
    1. Качи снимка на етикет
    2. Приложението разпознава текста
    3. Търси за вредни съставки:
       - 🇧🇬 Български имена
       - 🇬🇧 Английски имена
       - 🔢 Е-номера (E100-E999)
    """)
    
    st.header("📊 Статистика")
    st.metric("Общ брой вредни съставки", len(harmful_search_set))
    st.metric("Категории", len(harmful_ingredients_db))

# Основен интерфейс
tab1, tab2, tab3 = st.tabs(["📸 Анализ на етикет", "📚 Списък с вредни съставки", "➕ Добави нова"])

with tab1:
    uploaded_file = st.file_uploader("📸 Качи снимка на етикет", type=['jpg', 'jpeg', 'png'])
    
    col1, col2 = st.columns(2)
    with col1:
        languages = st.multiselect(
            "🌐 Езици за разпознаване",
            options=['en', 'bg', 'fr', 'de', 'it', 'es'],
            default=['en', 'bg']
        )
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Качена снимка", use_column_width=True)
        
        if st.button("🔍 Анализирай", type="primary"):
            with st.spinner("📖 Разпознаване на текст от изображение..."):
                # Запазване временно
                temp_path = "temp_upload.jpg"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # EasyOCR
                reader = easyocr.Reader(languages)
                result = reader.readtext(temp_path, detail=0, paragraph=True)
                full_text = " ".join(result)
                
                # Изтриване на временния файл
                os.remove(temp_path)
            
            # Показване на разпознатия текст
            with st.expander("📝 Разпознат текст", expanded=False):
                st.text(full_text[:1000] + ("..." if len(full_text) > 1000 else ""))
            
            # Търсене на вредни съставки
            with st.spinner("🔍 Търсене на вредни съставки..."):
                detected = detect_harmful_ingredients(full_text)
            
            # Показване на резултати
            st.subheader("🔬 Резултати от анализа")
            
            if detected:
                # Бройка
                harmful_count = len(detected)
                st.error(f"⚠️ **Открити {harmful_count} потенциално вредни съставки!**")
                
                # Таблица с резултатите
                results_data = []
                for item in detected:
                    # Иконка според типа
                    if item["type"] == "e_number":
                        icon = "🔢"
                    elif item["type"] == "bg_name":
                        icon = "🇧🇬"
                    else:
                        icon = "🇬🇧"
                    
                    results_data.append({
                        "Икона": icon,
                        "Открита съставка / Е-номер": item["term"].upper(),
                        "Категория": item["category"],
                        "Тип": "Е-номер" if item["type"] == "e_number" else ("Българско име" if item["type"] == "bg_name" else "Английско име")
                    })
                
                df_results = pd.DataFrame(results_data)
                st.dataframe(df_results, use_container_width=True)
                
                # Визуализация с предупреждения
                st.subheader("📋 Детайлен списък:")
                for item in detected:
                    if item["type"] == "e_number":
                        st.warning(f"🔢 **{item['term'].upper()}** → {item['category']}")
                    else:
                        st.warning(f"🧪 **{item['term'].title()}** → {item['category']}")
                
                # Експорт на резултатите
                csv = df_results.to_csv(index=False)
                st.download_button(
                    label="📥 Изтегли резултатите като CSV",
                    data=csv,
                    file_name="harmful_detections.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ **Не са открити вредни съставки!**")
                st.balloons()

with tab2:
    st.subheader("📋 Пълен списък на вредните съставки")
    
    # Подготовка на таблицата за показване
    table_data = []
    for category, data in harmful_ingredients_db.items():
        all_names = data["names_bg"] + data["names_en"]
        e_nums = ", ".join(data["e_numbers"]) if data["e_numbers"] else "-"
        
        for name in all_names:
            table_data.append({
                "Категория": category,
                "Име (български/английски)": name.title(),
                "Е-номер(и)": e_nums
            })
    
    df_full = pd.DataFrame(table_data)
    st.dataframe(df_full, use_container_width=True, height=400)
    
    # Филтър по категория
    categories = list(harmful_ingredients_db.keys())
    selected_cat = st.selectbox("🔍 Филтрирай по категория", ["Всички"] + categories)
    
    if selected_cat != "Всички":
        filtered_df = df_full[df_full["Категория"] == selected_cat]
        st.dataframe(filtered_df, use_container_width=True)
    
    # Експорт на целия списък
    st.download_button(
        label="📥 Изтегли пълния списък (CSV)",
        data=df_full.to_csv(index=False),
        file_name="all_harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("➕ Добавяне на нова вредна съставка")
    
    with st.form("add_ingredient_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_category = st.text_input("📂 Категория", placeholder="напр. Консерванти")
            new_name_bg = st.text_input("🇧🇬 Име на български", placeholder="напр. метилпарабен")
        
        with col2:
            new_name_en = st.text_input("🇬🇧 Име на английски", placeholder="напр. methylparaben")
            new_e_number = st.text_input("🔢 Е-номер", placeholder="напр. E218")
        
        submitted = st.form_submit_button("✅ Добави съставката")
        
        if submitted:
            if new_name_bg or new_name_en:
                st.success(f"✅ Добавено: {new_name_bg or new_name_en} → {new_category} (Е-номер: {new_e_number or '-'})")
                st.info("📌 За постоянно запазване, кодът трябва да бъде обновен или да се използва база данни (SQLite/JSON)")
            else:
                st.error("❌ Моля, въведи поне едно име!")

# Долен колонтитул
st.markdown("---")
st.markdown("📌 **Източник:** Базирано на Европейския списък на добавките (EU Food Additives) и INCI списъка")
