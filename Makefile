venv:
	python3.10 -m venv venv
	@echo "Run '. venv/bin/activate' to activate the virtual environment."
	
install:
	pip install -r requirements.txt

forecast:
	python3 forecast_model.py

run_dashboard:
	streamlit run app.py
