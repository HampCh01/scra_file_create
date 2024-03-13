FROM python:3.11
WORKDIR /app
RUN apt-get update && apt-get install -y gnupg
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "main"]