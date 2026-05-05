import streamlit as st
import easyocr
import re
from PIL import Image
import pandas as pd

# --- БАЗА ДАННИ (като горната) ---
harmful_ingredients_db = {
    "Консерванти (парабени)": {
        "names": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
        "e_numbers": []
    },
    "Формалдехид (консервант)": {
        "names": ["formaldehyde"],
        "e_numbers": ["E240"]
    },
    "Сулфати": {
        "names": ["sodium lauryl sulfate", "sodium laureth sulfate"],
        "e_numbers": []
    },
    "Изкуствени подсладители": {
        "names": ["aspartame", "saccharin"],
        "e_numbers": ["E951", "E954"]
    },
    "Вредни оцветители": {
        "names": ["tartrazine", "sunset yellow"],
        "e_numbers": ["E102", "E110"]
    },
    "Глутамат натрий": {
        "names": ["monosodium glutamate", "msg"],
        "e_numbers": ["E621"]
    },
    "Нитрити и нитрати": {
        "names": ["sodium nitrite"],
        "e_numbers": ["E250", "E251"]
    },
    "Бензоати": {
        "names": ["sodium benzoate"],
        "e_numbers": ["E211"]
    }
}

# Подготовка за търсене
search_data = []  # за таблицата

for category, data in harmful_ingredients_db.items():
    for name in data["names"]:
        search_data.append({
            "Категория": category,
            "Име на съставка": name.title(),
            "Е-номер": ", ".join(data["e_numbers"]) if data["e_numbers"] else "-"
        })
    for e_num in data["e_numbers"]:
        search_data.append({
            "Категория": category,
            "Име на съставка": "-",
            "Е-номер": e_num
        })

df_harmful = pd.DataFrame(search_data)

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
