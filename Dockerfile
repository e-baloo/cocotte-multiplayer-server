FROM python:3.11-alpine

WORKDIR /app

COPY serveur.py .

CMD ["python", "serveur.py"]

EXPOSE 5555
