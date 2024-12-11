install:
	python3.10 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

forecast:
	python3 forecast_model.py

run_dashboard:
	streamlit run app.py
