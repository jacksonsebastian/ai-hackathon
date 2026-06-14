FROM rocm/pytorch:latest

WORKDIR /app
COPY requirements.txt requirements-gpu.txt ./
RUN pip install -r requirements.txt && pip install -r requirements-gpu.txt

COPY . .

CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0"]
