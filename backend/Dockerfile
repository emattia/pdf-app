FROM python:3.12
WORKDIR /api
ENV POETRY_VIRTUALENVS_CREATE=false
RUN pip install poetry
COPY . .
RUN poetry install
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]