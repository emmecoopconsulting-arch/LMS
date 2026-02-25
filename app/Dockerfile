FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /srv
COPY requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv
RUN mkdir -p /data/uploads && chown -R app:app /srv /data/uploads

USER app

EXPOSE 8080
ENTRYPOINT ["/srv/entrypoint.sh"]
