.PHONY: run test install

install:
	pip install -r requirements.txt

install-gpu:
	pip install -r requirements.txt -r requirements-gpu.txt

run:
	streamlit run app/main.py

test:
	pytest tests/ -v
