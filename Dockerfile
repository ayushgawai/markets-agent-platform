FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .[service]
EXPOSE 8000
CMD ["python", "-m", "map_platform.api"]
