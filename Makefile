install:
	pip install -r requirements.txt

forecast:
	python3 forecast_model.py

run_dashboard:
	streamlit run app.py
