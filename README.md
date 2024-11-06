# CS506 Mid-semester Report #

CS506 MIDWAY REPORT VIDEO LINK: https://youtu.be/UaxeT2Xs02E
Project Proposal:

1. Description of the Project:

This project aims to develop a machine learning model capable of predicting crime patterns using data scraped from the Citizen App, complemented by other relevant datasets such as weather data, socioeconomic data, and historical crime reports in the decided locations. The project will identify potential trends and relationships between various factors influencing crime in urban areas. 

As of now, we have obtained a dataset of Boston crime incident reports from 2023 to the present, and have done preliminary visualizations and explorations of the data. Our future steps will be to create a regression model to predict the likelihood of a crime given features (e.g. day, time, location), as well as scrape the Citizen App for realtime predictions.

2. Clear Goals:

The main objectives of this project are:

    Successfully predict crime hotspots in a city based on previous crime data.
    Identify patterns and trends associated with different types of crimes (e.g., theft, assault).
    Provide predictions that can help in deploying law enforcement resources more effectively.

3. Data Collection:

We will be collecting the following data:

    Crime data: This data can be scraped from CitizenApp using their public crime reports. Data will include type of crime and response time from authorities.
    Location data: GPS coordinates of where crimes occurred.
    Temporal data: Date, time of day, and day of the week.
    Additional factors: Weather data, neighborhood features (e.g., residential or commercial areas), population density.

So far, we have obtained crime, location, and temporal data. We will assess the need of additional data such as weather and population density in the future as we create the regression model.

Data will be collected via web scraping tools or APIs like https://stevesie.com/apps/citizen-api. If needed, we will use publicly available datasets from government sources like the FBI or local police departments to complement the CitizenApp data.
4. Data Modeling:

The modeling will involve:

    Logistic regression or random forest will be used as a baseline model.
    Time series analysis to predict crime trends over time.
    Regression models (e.g. random forests, or XGBoost) to predict crime count or crime severity given features such as time of day, location, etc.
    Potential use of deep learning models like LSTM (for time series data), or geospatial decision trees (for geographical information).

5. Data Visualization:

We plan to visualize the data using:

    Heatmaps to show crime density across various neighborhoods.
    Time series plots to highlight crime trends over time.
    Interactive maps with crime predictions overlaid on top of real-time city maps.
    Scatter plots and histograms to show the relationships between crime rates and other factors like time of day, weather, and location.

![incident_treemap](https://github.com/user-attachments/assets/dae1b0f8-00f9-4ee6-b663-f10880ecddb2)
Figure 1. Treemap of major crime incident reports in Boston. The top 5 crime incidents are: investigate person, sick assist, motor vehicle leaving scene with property damage, investigate property, and towed motor vehicle. 

![dav_vs_night_incident](https://github.com/user-attachments/assets/19a59f80-ea29-495e-9d52-076687bff4be)

Figure 2. Incident count in the day vs. night. There have been around 60,000 incident reports from 2023 to the present in the night time, and around 80,000 reports in the day time. 

![density_plot_incidents](https://github.com/user-attachments/assets/5db904a0-b472-4f08-a567-abfdcc560135)

Figure 3. Density plot of incident reports. We see that there is a larger density of incident reports around long. -71.05 and lat. 42.35. 

6. Test Plan:

We will implement the following testing strategy:

    Collect daily data.
    Split the data into a training set (5/7) and a test set (2/7) randomly (2 days from each week goes into Testing, and the rest goes into training).
    Cross-validation to fine-tune the model parameters.
    Time-based splitting: We may train the model on data from the past months and test it on the most recent data to mimic real-world predictive scenarios.

