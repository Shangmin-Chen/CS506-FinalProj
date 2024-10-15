# CS506-FinalProj

Project Proposal:

1. Description of the Project:

We aim to develop a crime predictor model using real-time crime data from the CitizenApp. The goal is to predict the likelihood of specific types of crimes occurring in various neighborhoods based on historical data, time of day, and other environmental factors.
2. Clear Goals:

The main objectives of this project are:

    Successfully predict crime hotspots in a city based on previous crime data.
    Identify patterns and trends associated with different types of crimes (e.g., theft, assault).
    Provide predictions that can help in deploying law enforcement resources more effectively.

3. Data Collection:

We will be collecting the following data:

    Historical crime data: This data can be scraped from CitizenApp using their public crime reports.
    Location data: GPS coordinates of where crimes occurred.
    Temporal data: Date, time of day, and day of the week.
    Additional factors: Weather data, neighborhood features (e.g., residential or commercial areas).

Data will be collected via web scraping tools or APIs like https://stevesie.com/apps/citizen-api. If needed, we will use publicly available datasets from government sources like the FBI or local police departments to complement the CitizenApp data.
4. Data Modeling:

The modeling will involve:

    Clustering methods to identify crime hotspots.
    Time series analysis to predict crime trends over time.
    Classification models (e.g., decision trees, random forests, or XGBoost) to predict specific types of crimes.
    Potential use of deep learning models like LSTM (Most likely because we are doing time series) or CNNs if the data size justifies it.

5. Data Visualization:

We plan to visualize the data using:

    Heatmaps to show crime density across various neighborhoods.
    Time series plots to highlight crime trends over time.
    Interactive maps with crime predictions overlaid on top of real-time city maps.
    Scatter plots and histograms to show the relationships between crime rates and other factors like time of day, weather, and location.

6. Test Plan:

We will implement the following testing strategy:

    Collect daily data.
    Split the data into a training set (5/7) and a test set (2/7) randomly (2 days from each week goes into Testing, and the rest goes into training).
    Cross-validation to fine-tune the model parameters.
    Time-based splitting: We may train the model on data from the past months and test it on the most recent data to mimic real-world predictive scenarios.
