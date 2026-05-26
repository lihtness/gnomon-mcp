FROM python:3.12-slim

RUN pip install --no-cache-dir gnomon-mcp==0.1.2

ENTRYPOINT ["gnomon-mcp"]
CMD ["--transport", "stdio"]
