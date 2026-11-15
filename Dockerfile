FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5

WORKDIR /app

COPY requirements.txt .

# If you in iran , you can uncomment this line instead of line 19 so it uses a mirror for pip packages.
# RUN pip install --no-cache-dir \
#     -i https://mirror-pypi.runflare.com/simple \
#     --trusted-host mirror-pypi.runflare.com \
#     -r requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
 

COPY . .
COPY wait-for-db.sh /wait-for-db.sh

RUN chmod +x /wait-for-db.sh

ENTRYPOINT ["/wait-for-db.sh"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]