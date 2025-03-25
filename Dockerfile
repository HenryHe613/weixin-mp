FROM python:3.11.2-slim
LABEL auther="nanyancc"

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]