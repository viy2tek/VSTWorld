FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY vstworld ./vstworld
COPY sources.json ./sources.json
COPY LICENSE ./LICENSE
RUN mkdir /data && chown 10001:10001 /data
ENV VSTWORLD_SOURCES=/data/sources.json
USER 10001:10001
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health', timeout=2)"
CMD ["python", "-m", "vstworld", "--host", "0.0.0.0"]
