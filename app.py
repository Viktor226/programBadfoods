import streamlit as st
import pytesseract
import cv2
import numpy as np
import pandas as pd
import re
from PIL import Image
import os

# --- Конфигурация на страницата ---
st.set_page_config(
    page_title="Анализатор на вредни съставки",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Анализатор на вредни съставки")
st.markdown("**Автоматично разпознаване на текст от снимка + обяснение защо са вредни**")

# --- БАЗА ДАННИ С ВРЕДНИ СЪСТАВКИ И ОПИСАНИЯ ---
harmful_db = {
     "Карамел (E150d) - оцветител": {
        "bg": ["карамел", "карамелен оцветител", "амонячно-сулфитен карамел"],
        "en": ["caramel colour", "caramel", "ammonia caramel", "sulphite ammonia caramel"],
        "e": ["E150d"],
        "description": "Съдържа 4-метилимидазол (4-MEI) - потенциален канцероген при високи дози. Може да предизвика алергични реакции при чувствителни хора. Някои проучвания сочат връзка с хиперактивност при деца.",
        "used_for": "Оцветител в безалкохолни напитки (Кока-Кола, Пепси), сосове, бира, сладкиши"
    },
    "Калиев нитрат (E252) - консервант": {
        "bg": ["калиев нитрат", "еликсир", "калиева селитра"],
        "en": ["potassium nitrate", "saltpeter"],
        "e": ["E252"],
        "description": "В организма се превръща в нитрити, които могат да образуват нитрозамини - доказани канцерогени. Свързва се с рак на стомаха и хранопровода. Може да причини метхемоглобинемия (нарушава преноса на кислород в кръвта).",
        "used_for": "Консервант в месни продукти (салами, шунка, бекон), твърди сирена, рибни продукти"
    },
    "Калиев нитрит (E249) - консервант": {
        "bg": ["калиев нитрит"],
        "en": ["potassium nitrite"],
        "e": ["E249"],
        "description": "Силно токсичен в големи количества. При нагряване и в стомаха може да образува канцерогенни нитрозамини. Свързва се с рак на дебелото черво и панкреаса. Може да предизвика главоболие, замаяност и причерняване.",
        "used_for": "Консервант и фиксатор на цвета в месни продукти (колбаси, бекон, консерви)"
    },
    "Натриев аскорбат (E301) - антиоксидант": {
        "bg": ["натриев аскорбат", "натриева сол на аскорбиновата киселина"],
        "en": ["sodium ascorbate", "sodium L-ascorbate"],
        "e": ["E301"],
        "description": "Самият по себе си е безопасен и е форма на витамин С. Основният проблем е, че в комбинация с нитрати и нитрити може да ускори образуването на канцерогенни нитрозамини в месните продукти. При предозиране може да причини стомашно разстройство и диария.",
        "used_for": "Антиоксидант в месни продукти (предпазва от гранясване), плодови сокове, бира, брашно"
    }
    "Парабени (консерванти)": {
        "bg": ["метилпарабен", "етилпарабен", "пропилпарабен", "бутилпарабен"],
        "en": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
        "e": [],
        "description": "Свързват се с хормонални нарушения, имитират естроген и могат да повлияят на репродуктивната система. Някои проучвания сочат връзка с рак на гърдата.",
        "used_for": "Консервант против мухъл, бактерии и дрожди в козметика и храни"
    },
    "Сулфати (пянообразуватели)": {
        "bg": ["натриев лаурил сулфат", "натриев лаурет сулфат"],
        "en": ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"],
        "e": [],
        "description": "Дразнят кожата, очите и скалпа. Могат да причинят дерматит, акне и да изсушават косата. При дългосрочна употреба увреждат кожната бариера.",
        "used_for": "Пянообразувател в шампоани, пасти за зъби, сапуни"
    },
    "Формалдехид": {
        "bg": ["формалдехид"],
        "en": ["formaldehyde"],
        "e": ["E240"],
        "description": "Канцероген от категория 1 (доказан при хора). Може да причини алергични реакции, дразнене на дихателните пътища, астма и главоболие.",
        "used_for": "Консервант, дезинфектант, в козметиката"
    },
    "Аспартам": {
        "bg": ["аспартам"],
        "en": ["aspartame"],
        "e": ["E951"],
        "description": "Свързва се с главоболие, световъртеж, промени в настроението, депресия. Противопоказен за хора с фенилкетонурия.",
        "used_for": "Подсладител в безалкохолни напитки, дъвки, десерти"
    },
    "Глутамат натрий (MSG)": {
        "bg": ["мононатриев глутамат", "глутаминова киселина"],
        "en": ["monosodium glutamate", "msg"],
        "e": ["E621"],
        "description": "Може да предизвика главоболие, гадене, слабост, сърцебиене. При чувствителни хора причинява астматични пристъпи.",
        "used_for": "Усилвател на вкуса в готови храни, чипсове, супи"
    },
    "Натриев бензоат": {
        "bg": ["натриев бензоат", "бензоена киселина"],
        "en": ["sodium benzoate", "benzoic acid"],
        "e": ["E211", "E210"],
        "description": "В комбинация с витамин С може да образува бензен - доказан канцероген. Може да предизвика алергични реакции.",
        "used_for": "Консервант в безалкохолни напитки, сосове, сладка"
    },
    "Тартразин (E102)": {
        "bg": ["тартразин"],
        "en": ["tartrazine"],
        "e": ["E102"],
        "description": "Може да предизвика алергични реакции, обриви, астма. Свързва се с хиперактивност при деца (ADHD).",
        "used_for": "Жълт оцветител в бонбони, напитки, десерти"
    },
    "Захарин": {
        "bg": ["захарин", "сахарин"],
        "en": ["saccharin"],
        "e": ["E954"],
        "description": "В миналото е бил свързван с рак на пикочния мехур при животни. Остава противоречив подсладител.",
        "used_for": "Подсладител в диетични напитки и нискокалорични храни"
    },
    "BHA / BHT": {
        "bg": ["бутилхидроксианизол", "бутилхидрокситолуен"],
        "en": ["bha", "bht"],
        "e": ["E320", "E321"],
        "description": "Класифицирани като 'възможни канцерогени за човека'. Могат да повлияят на хормоналния баланс.",
        "used_for": "Консерванти в мазнини, масла, зърнени закуски"
    },
    "Цикламат": {
        "bg": ["цикламат"],
        "en": ["cyclamate"],
        "e": ["E952"],
        "description": "Забранен в САЩ поради съмнения за канцерогенност. Може да причини увреждане на тестисите.",
        "used_for": "Подсладител в нискокалорични храни и напитки"
    },
    "Ацесулфам К": {
        "bg": ["ацесулфам"],
        "en": ["acesulfame k"],
        "e": ["E950"],
        "description": "Проучвания сочат възможна връзка с тумори при лабораторни животни. Може да стимулира отделянето на инсулин.",
        "used_for": "Подсладител в безалкохолни напитки, сладкиши"
    },
    "Калиев сорбат": {
        "bg": ["калиев сорбат"],
        "en": ["potassium sorbate"],
        "e": ["E202"],
        "description": "Може да предизвика алергични реакции, дразнене на кожата и очите.",
        "used_for": "Консервант в сирена, вина, сосове, козметика"
    }
}

# --- Функция за търсене на вредни съставки ---
def find_harmful_ingredients(text):
    """Търси вредни съставки в текста и връща списък с описания"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_items = []
    seen_terms = set()
    
    # Търсене във всички категории
    for category, data in harmful_db.items():
        # Обединяваме всички термини за търсене
        all_terms = []
        all_terms.extend([name.lower() for name in data["bg"]])
        all_terms.extend([name.lower() for name in data["en"]])
        all_terms.extend([e_num.lower() for e_num in data["e"]])
        
        for term in all_terms:
            if term in text_lower and term not in seen_terms:
                seen_terms.add(term)
                found_items.append({
                    "term": term.upper(),
                    "category": category,
                    "description": data["description"],
                    "used_for": data["used_for"]
                })
                break  # Спираме след първото съвпадение в категорията
    
    # Търсене на Е-номера (допълнително)
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e_code in e_matches:
        e_upper = f"E{e_code[1:].upper()}"
        if e_upper.lower() not in seen_terms:
            # Търсим в базата дали този Е-номер съществува
            for category, data in harmful_db.items():
                if e_upper in data["e"]:
                    seen_terms.add(e_upper.lower())
                    found_items.append({
                        "term": e_upper,
                        "category": category,
                        "description": data["description"],
                        "used_for": data["used_for"]
                    })
                    break
    
    return found_items

# --- Функция за разпознаване на текст от изображение ---
def extract_text_from_image(image_file):
    """Разпознава текст от снимка с Tesseract OCR"""
    try:
        # Четене на изображението
        image = Image.open(image_file)
        img_array = np.array(image)
        
        # Конвертиране към RGB
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Преобразуване в сива скала
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # Подобряване на качеството
        gray = cv2.medianBlur(gray, 1)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Разпознаване на текст
        text = pytesseract.image_to_string(gray, lang='bul+eng')
        return text
    except Exception as e:
        st.error(f"Грешка при разпознаване: {str(e)}")
        return ""

# --- Streamlit интерфейс ---
tab1, tab2, tab3 = st.tabs(["📸 Анализ на снимка", "📋 Списък с вредни съставки", "ℹ️ Помощ"])

with tab1:
    st.subheader("📸 Качи снимка на етикет")
    
    uploaded_file = st.file_uploader(
        "Избери снимка (JPG, JPEG, PNG)",
        type=['jpg', 'jpeg', 'png']
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Вашата снимка", use_column_width=True)
        
        with col2:
            if st.button("🔍 АНАЛИЗИРАЙ СНИМКАТА", type="primary", use_container_width=True):
                with st.spinner("📖 Разпознаване на текст от изображение..."):
                    recognized_text = extract_text_from_image(uploaded_file)
                
                with st.expander("📝 Разпознат текст от снимката", expanded=False):
                    if recognized_text.strip():
                        st.text(recognized_text[:800])
                    else:
                        st.warning("⚠️ Не беше разпознат текст. Опитай с по-ясна снимка.")
                
                # Алтернативно ръчно въвеждане
                manual_text = st.text_area("✏️ Или въведи съставките ръчно:", key="manual_input", height=100)
                
                text_for_analysis = manual_text if manual_text else recognized_text
                
                if text_for_analysis:
                    with st.spinner("🔍 Търсене на вредни съставки..."):
                        harmful_items = find_harmful_ingredients(text_for_analysis)
                    
                    st.markdown("---")
                    st.subheader("🔬 РЕЗУЛТАТИ ОТ АНАЛИЗА")
                    
                    if harmful_items:
                        st.error(f"⚠️ **Открити {len(harmful_items)} вредни съставки!**")
                        
                        # Показване на всяка съставка с описание в разгъващ се панел
                        for item in harmful_items:
                            with st.expander(f"❌ **{item['term']}** → {item['category']}", expanded=True):
                                st.markdown(f"**🔬 За какво се използва:** {item['used_for']}")
                                st.markdown(f"**⚠️ Защо е вредна:** {item['description']}")
                        
                        # Таблица за експорт
                        df_results = pd.DataFrame(harmful_items)
                        df_results = df_results.rename(columns={
                            "term": "Съставка",
                            "category": "Категория",
                            "used_for": "Употреба",
                            "description": "Описание на вредата"
                        })
                        csv = df_results.to_csv(index=False)
                        st.download_button(
                            label="📥 Изтегли резултатите (CSV)",
                            data=csv,
                            file_name="harmful_detections.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ!**")
                        st.balloons()

with tab2:
    st.subheader("📋 Пълен списък на вредните съставки с описания")
    
    # Създаване на таблица
    table_data = []
    for category, data in harmful_db.items():
        all_names = data["bg"] + data["en"]
        e_nums = ", ".join(data["e"]) if data["e"] else "-"
        for name in all_names:
            table_data.append({
                "Категория": category,
                "Съставка": name.title(),
                "Е-номер(и)": e_nums,
                "Употреба": data["used_for"],
                "Вреда": data["description"][:100] + "..."
            })
    
    df_full = pd.DataFrame(table_data)
    st.dataframe(df_full, use_container_width=True, height=400)
    
    st.download_button(
        label="📥 Изтегли пълния списък (CSV)",
        data=df_full.to_csv(index=False),
        file_name="all_harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("ℹ️ Как да използваш приложението")
    st.markdown("""
    1. **Качи снимка** на етикет на продукт
    2. Натисни **„Анализирай снимката“**
    3. Ако OCR не разпознае добре текста, въведи съставките **ръчно**
    4. Разгледай резултатите - за всяка вредна съставка ще видиш:
       - За какво се използва
       - Защо е вредна за здравето
    
    ### Какво разпознава приложението?
    - Парабени, сулфати, формалдехид
    - Подсладители (аспартам, захарин, цикламат, ацесулфам)
    - Консерванти (бензоати, сорбати, пропионати)
    - Оцветители (тартразин, сончев залез)
    - Усилватели на вкуса (глутамат)
    - Е-номера (E102, E110, E202, E211, E240, E320, E321, E621, E950, E951, E952, E954)
    """)

st.markdown("---")
st.caption("📌 Приложението е информативно и не замества медицинска консултация")
