# Python 3.10 asosidagi rasm
FROM python:3.13-slim

# Ishchi katalog yaratish
WORKDIR /app

# Python kutubxonalarni o‘rnatish uchun fayllarni ko‘chirish
COPY requirements.txt .

# Kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Kod fayllarini konteynerga ko‘chirish
COPY . .

# Botni ishga tushirish
CMD ["python", "run.py"]
