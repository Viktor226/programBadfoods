import easyocr
import cv2
import re
from pathlib import Path

# --- База данни с вредни съставки ---
harmful_ingredients_db = {
    "parabens": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben", "isobutylparaben"],
    "sulfates": ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"],
    "phthalates": ["dep", "dbp", "bbp", "dehp", "dinp", "didp"],
    "formaldehyde releasers": ["formaldehyde", "dmdm hydantoin", "quaternium-15", "imidazolidinyl urea", "diazolidinyl urea"],
    "silicones": ["dimethicone", "cyclomethicone", "cyclotetrasiloxane", "cyclopentasiloxane"],
    "mineral oil": ["mineral oil", "paraffinum liquidum", "petrolatum", "vaseline"],
    "alcohol denat": ["alcohol denat", "denatured alcohol", "sd alcohol"],
    "fragrance allergens": ["limonene", "linalool", "coumarin", "eugenol", "citronellol"]
}

# Превръщаме всичко в малки букви за бързо търсене
harmful_set = set()
for category, ingredients in harmful_ingredients_db.items():
    for ing in ingredients:
        harmful_set.add(ing.lower())

# --- Функция за извличане на съставки от текст ---
def extract_ingredients_from_text(text):
    """Извлича списък със съставки от текста"""
    text_lower = text.lower()
    
    # Търси секция със съставки
    patterns = [
        r"ingredients:\s*(.*?)(?:\n\n|\Z)",
        r"inci:\s*(.*?)(?:\n\n|\Z)",
        r"съставки:\s*(.*?)(?:\n\n|\Z)",
        r"composition:\s*(.*?)(?:\n\n|\Z)"
    ]
    
    ingredients_text = ""
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.DOTALL)
        if match:
            ingredients_text = match.group(1)
            break
    
    if not ingredients_text:
        ingredients_text = text_lower
    
    # Разделяне на отделни съставки
    ingredients_list = re.split(r'[,;\n\.]', ingredients_text)
    ingredients_list = [ing.strip() for ing in ingredients_list if len(ing.strip()) > 2]
    
    return ingredients_list

# --- Функция за разпознаване на текст от изображение с EasyOCR ---
def recognize_ingredients_from_image(image_path, languages=['en', 'bg']):
    """
    Разпознава текст от изображение
    languages: ['en'] за английски, ['bg'] за български, ['en','bg'] и за двата
    """
    print(f"📸 Обработка на изображение: {image_path}")
    
    # Инициализиране на EasyOCR четеца
    reader = easyocr.Reader(languages)  # автоматично тегли нужните модели
    
    # Прочитане на изображението
    result = reader.readtext(image_path, detail=0, paragraph=True)
    
    # Обединяване на целия текст
    full_text = " ".join(result)
    print(f"📝 Разпознат текст:\n{full_text[:500]}...\n")
    
    return full_text

# --- Основна функция за проверка на вредни съставки ---
def check_harmful_ingredients(source_path, languages=['en', 'bg']):
    """
    Проверява дали в продукта има вредни съставки
    
    source_path: път към изображение или текстов файл
    languages: езици за OCR ('en', 'bg', 'fr', 'de' и др.)
    """
    
    # Определяне на типа вход
    file_ext = Path(source_path).suffix.lower()
    
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        # Разпознаване от изображение
        text = recognize_ingredients_from_image(source_path, languages)
    elif file_ext in ['.txt', '.csv']:
        # Четене от текстов файл
        print(f"📄 Четене от текстов файл: {source_path}")
        with open(source_path, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        # Ако е директен текст
        print("📝 Обработка на директен текст")
        text = source_path
    
    # Извличане на списъка със съставки
    ingredients = extract_ingredients_from_text(text)
    print(f"🔍 Намерени {len(ingredients)} потенциални съставки")
    
    # Търсене на вредни съставки
    detected_harmful = []
    
    for ingredient in ingredients:
        # Проверка за директно съвпадение
        if ingredient in harmful_set:
            detected_harmful.append(ingredient)
        else:
            # Проверка за частични съвпадения (напр. "methylparaben" съдържа "paraben")
            for harmful in harmful_set:
                if harmful in ingredient or ingredient in harmful:
                    detected_harmful.append(ingredient)
                    break
    
    # Премахване на дубликати
    detected_harmful = list(set(detected_harmful))
    
    # Показване на резултатите
    print("\n" + "="*50)
    if detected_harmful:
        print(f"⚠️ **ОТКРИТИ ВРЕДНИ СЪСТАВКИ: {len(detected_harmful)}**")
        print("="*50)
        
        for bad in detected_harmful:
            # Намери категорията на вредната съставка
            category_found = None
            for category, ingredients_list in harmful_ingredients_db.items():
                if bad in ingredients_list:
                    category_found = category
                    break
            
            if category_found:
                print(f"❌ {bad.upper()} → Категория: {category_found}")
            else:
                print(f"❌ {bad.upper()}")
    else:
        print("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ**")
        print("(спрямо текущата база данни)")
    
    print("="*50)
    
    return detected_harmful

# --- Функция за добавяне на нова вредна съставка ---
def add_harmful_ingredient(ingredient_name, category):
    """Добавя нова вредна съставка в базата данни"""
    ingredient_lower = ingredient_name.lower()
    if category in harmful_ingredients_db:
        harmful_ingredients_db[category].append(ingredient_lower)
    else:
        harmful_ingredients_db[category] = [ingredient_lower]
    
    harmful_set.add(ingredient_lower)
    print(f"✅ Добавена: {ingredient_name} → {category}")

# --- ИНТЕРАКТИВЕН ИНТЕРФЕЙС ---
def main():
    print("="*50)
    print("🛡️ АНАЛИЗАТОР НА ВРЕДНИ СЪСТАВКИ с EasyOCR")
    print("="*50)
    
    while True:
        print("\nИзбери опция:")
        print("1️⃣ Анализирай снимка на етикет")
        print("2️⃣ Анализирай текстов файл със съставки")
        print("3️⃣ Въведи текст на ръка")
        print("4️⃣ Добави нова вредна съставка")
        print("5️⃣ Изход")
        
        choice = input("\n👉 Избери (1-5): ").strip()
        
        if choice == "1":
            image_path = input("📸 Път към снимката: ").strip()
            if Path(image_path).exists():
                check_harmful_ingredients(image_path)
            else:
                print("❌ Файлът не съществува!")
        
        elif choice == "2":
            file_path = input("📄 Път към текстовия файл: ").strip()
            if Path(file_path).exists():
                check_harmful_ingredients(file_path)
            else:
                print("❌ Файлът не съществува!")
        
        elif choice == "3":
            print("📝 Въведи списъка със съставки (напр. 'Aqua, Glycerin, Sodium Lauryl Sulfate'):")
            text_input = input("Съставки: ").strip()
            if text_input:
                # Запазваме като временен файл
                temp_file = "temp_ingredients.txt"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(f"Ingredients: {text_input}")
                check_harmful_ingredients(temp_file)
                Path(temp_file).unlink()  # Изтриваме временния файл
        
        elif choice == "4":
            name = input("🔬 Име на вредната съставка: ").strip()
            category = input("📂 Категория (напр. parabens, sulfates): ").strip()
            add_harmful_ingredient(name, category)
        
        elif choice == "5":
            print("👋 Благодаря за използването!")
            break
        
        else:
            print("❌ Невалиден избор!")

# --- ПРИМЕР ЗА ДИРЕКТНО ИЗПЪЛНЕНИЕ ---
if __name__ == "__main__":
    # Примерен тест
    test_image = "product_label.jpg"  # Ако имаш такава снимка
    
    # Ако искаш директно тестване без интерфейс:
    # check_harmful_ingredients("test_image.jpg", languages=['en', 'bg'])
    
    # Стартиране на интерактивния режим
    main()
