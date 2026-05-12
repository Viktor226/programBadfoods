import streamlit as st
from PIL import Image
import pandas as pd
import re

# Конфигурация за страницата
st.set_page_config(
    page_title="Анализатор на вредни съставки",
    page_icon="🛡️",
    layout="wide"
)

# Заглавие
st.title("🛡️ Анализатор на вредни съставки")
st.markdown("Качи снимка на етикет и ще разпознаем вредните съставки")

# --- БАЗА ДАННИ С ВРЕДНИ СЪСТАВКИ (БЪЛГАРСКИ + АНГЛИЙСКИ + Е-НОМЕРА) ---
harmful_ingredients_db = {
    "Парабени (консерванти)": {
        "names_bg": ["метилпарабен", "етилпарабен", "пропилпарабен", "бутилпарабен"],
        "names_en": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
        "e_numbers": []
    },
    "Сулфати (пянообразуватели)": {
        "names_bg": ["натриев лаурил сулфат", "натриев лаурет сулфат"],
        "names_en": ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"],
        "e_numbers": []
    },
    "Формалдехид": {
        "names_bg": ["формалдехид"],
        "names_en": ["formaldehyde"],
        "e_numbers": ["E240"]
    },
    "Изкуствени подсладители": {
        "names_bg": ["аспартам", "захарин", "сукралоза"],
        "names_en": ["aspartame", "saccharin", "sucralose"],
        "e_numbers": ["E951", "E954", "E955"]
    },
    "Вредни оцветители": {
        "names_bg": ["тартразин", "сончев залез", "азорубин"],
        "names_en": ["tartrazine", "sunset yellow", "azorubine"],
        "e_numbers": ["E102", "E110", "E122"]
    },
    "Глутамат натрий": {
        "names_bg": ["мононатриев глутамат", "глутаминова киселина"],
        "names_en": ["monosodium glutamate", "msg"],
        "e_numbers": ["E621"]
    },
    "Бензоати": {
        "names_bg": ["натриев бензоат", "бензоена киселина"],
        "names_en": ["sodium benzoate", "benzoic acid"],
        "e_numbers": ["E211", "E210"]
    },
    "Нитрати и нитрити": {
        "names_bg": ["натриев нитрат", "натриев нитрит"],
        "names_en": ["sodium nitrate", "sodium nitrite"],
        "e_numbers": ["E251", "E250"]
    }
}

# Подготовка за търсене
harmful_search_set = set()
ingredient_info = {}

for category, data in harmful_ingredients_db.items():
    for name in data["names_bg"]:
        name_lower = name.lower()
        harmful_search_set.add(name_lower)
        ingredient_info[name_lower] = {"category": category, "type": "bg"}
    
    for name in data["names_en"]:
        name_lower = name.lower()
        harmful_search_set.add(name_lower)
        ingredient_info[name_lower] = {"category": category, "type": "en"}
    
    for e_num in data["e_numbers"]:
        harmful_search_set.add(e_num.upper())
        ingredient_info[e_num.upper()] = {"category": category, "type": "e"}

# --- Функция за разпознаване на текст (без EasyOCR - само симулация за тест) ---
def detect_harmful_from_text(text):
    """Търси вредни съставки в текст"""
    text_lower = text.lower()
    detected = []
    
    # Търсене на Е-номера
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e_num in e_matches:
        e_num_upper = f"E{e_num[1:].upper()}"
        if e_num_upper in harmful_search_set:
            detected.append({
                "term": e_num_upper,
                "category": ingredient_info[e_num_upper]["category"],
                "type": "Е-номер"
            })
    
    # Търсене на имена
    for harmful in harmful_search_set:
        if harmful in text_lower and not harmful.startswith('e'):
            if len(harmful) > 3:  # игнорираме твърде кратки думи
                detected.append({
                    "term": harmful,
                    "category": ingredient_info[harmful]["category"],
                    "type": "Българско" if ingredient_info[harmful]["type"] == "bg" else "Английско"
                })
    
    # Премахване на дубликати
    unique = []
    seen = set()
    for d in detected:
        key = (d["term"], d["category"])
        if key not in seen:
            seen.add(key)
            unique.append(d)
    
    return unique

# --- Streamlit интерфейс ---
tab1, tab2, tab3 = st.tabs(["📸 Анализ на етикет", "📚 Списък с вредни съставки", "ℹ️ Инструкции"])

with tab1:
    uploaded_file = st.file_uploader("Качи снимка на етикет", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        # Показване на снимката
        image = Image.open(uploaded_file)
        st.image(image, caption="Качена снимка", use_column_width=True)
        
        # Ръчно въвеждане на текст (заради липсата на OCR в облака)
        st.markdown("---")
        st.info("📝 **Важно:** Поради технически ограничения в Streamlit Cloud, моля, въведи текста от етикета ръчно:")
        
        manual_text = st.text_area(
            "Въведи съставките от етикета:",
            placeholder="Пример: Aqua, Sodium Lauryl Sulfate, Methylparaben, Glycerin, E211",
            height=150
        )
        
        if st.button("🔍 Анализирай", type="primary"):
            if manual_text:
                with st.spinner("Анализиране на съставките..."):
                    detected = detect_harmful_from_text(manual_text)
                
                if detected:
                    st.error(f"⚠️ **Открити {len(detected)} потенциално вредни съставки!**")
                    
                    # Таблица с резултатите
                    results_data = []
                    for item in detected:
                        results_data.append({
                            "Съставка / Е-номер": item["term"].upper(),
                            "Категория": item["category"],
                            "Тип": item["type"]
                        })
                    
                    df_results = pd.DataFrame(results_data)
                    st.dataframe(df_results, use_container_width=True)
                    
                    # Детайлен списък
                    for item in detected:
                        st.warning(f"⚠️ **{item['term'].upper()}** → {item['category']}")
                else:
                    st.success("✅ **Не са открити вредни съставки!**")
                    st.balloons()
            else:
                st.warning("Моля, въведи текст за анализ")

with tab2:
    st.subheader("📋 Списък на вредните съставки")
    
    # Създаване на таблица
    table_data = []
    for category, data in harmful_ingredients_db.items():
        all_names = data["names_bg"] + data["names_en"]
        e_nums = ", ".join(data["e_numbers"]) if data["e_numbers"] else "-"
        
        for name in all_names:
            table_data.append({
                "Категория": category,
                "Име на съставка": name.title(),
                "Е-номер(и)": e_nums
            })
    
    df_full = pd.DataFrame(table_data)
    st.dataframe(df_full, use_container_width=True, height=400)
    
    # Експорт
    st.download_button(
        label="📥 Изтегли списъка (CSV)",
        data=df_full.to_csv(index=False),
        file_name="harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("📖 Как да използваш приложението")
    st.markdown("""
    1. **Качи снимка** на етикета на продукта
    2. **Въведи текста** от етикета в полето (съставките)
    3. Натисни **"Анализирай"**
    
    ### 🔍 Какво търси приложението?
    - 🇧🇬 Български имена на вредни съставки
    - 🇬🇧 Английски имена на вредни съставки  
    - 🔢 Е-номера (E100-E999)
    
    ### ⚠️ Важно
    Това приложение е **информативно** и не замества консултация със специалист.
    """)

# Долен колонтитул
st.markdown("---")
st.markdown("📌 **База данни:** Парабени, сулфати, оцветители, консерванти и други вредни добавки")
