# Usa un'immagine ufficiale di Python leggera
FROM python:3.11-slim

# Ottimizza i log di Python su Docker in modo nativo
ENV PYTHONUNBUFFERED=1

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia solo il file requirements.txt per sfruttare la cache di Docker
COPY backend/requirements.txt ./backend/

# Installa le dipendenze senza salvare la cache di pip (riduce il peso dell'immagine)
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copia il resto del codice dell'applicazione nel container
COPY . .

# Esponi la porta su cui l'app è in ascolto (es. 8000 per FastAPI/Django, 5000 per Flask)
EXPOSE 6060

# Comando di default per avviare l'applicazione
CMD ["python", "frontend/app.py"]
