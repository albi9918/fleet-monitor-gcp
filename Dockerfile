# Usa un'immagine Python ufficiale come base
FROM python:3.9-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Copia il file delle dipendenze
COPY requirements.txt requirements.txt

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice del progetto nel container
COPY . .

# Comando per avviare l'applicazione Flask quando il container parte
# Usiamo gunicorn come server WSGI, più robusto di quello di sviluppo di Flask
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]