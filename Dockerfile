FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/verdi-forum-nord/fluxcd-nextcloud-talk-bridge

WORKDIR /app

# Copy the app
COPY app.py /app/

# Install required packages
RUN pip install flask gunicorn requests --no-cache-dir

# Expose the port
EXPOSE 8080

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]