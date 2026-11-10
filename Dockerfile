FROM python:3.13-slim-bookworm
# Recurring events and civil-day availability require the IANA timezone DB.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/calendar
COPY calendar_app/ calendar_app/
COPY web/ web/
RUN groupadd -r calendar && useradd -r -g calendar -u 10001 calendar \
    && mkdir /data && chown calendar:calendar /data
USER 10001:10001
ENV GC_CALENDAR_DB=/data/calendar.sqlite3 \
    GC_CALENDAR_HOST=0.0.0.0 \
    GC_CALENDAR_PORT=8787 \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8787
CMD ["python","-m","calendar_app","serve"]
