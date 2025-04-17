FROM python:3.11.2-slim
LABEL auther="nanyancc"

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

CMD ["python", "main.py"]