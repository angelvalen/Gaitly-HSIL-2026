# CIPN Gait Analyzer

Web application for live smartphone-based gait acquisition and AI-assisted analysis of chemotherapy-induced peripheral neuropathy (CIPN) risk.

The system connects to a mobile device running Phyphox, collects IMU data in real time, extracts biomechanical and clinical features, runs an ML model, and stores the final test results in a SQLite database.

---

## Overview

This project provides:

- Live gait acquisition from a smartphone through **Phyphox**
- Real-time signal preview during the test
- Automatic feature extraction from accelerometer and gyroscope data
- AI-based CIPN risk estimation
- Clinical-style dashboard with test history and derived metrics
- SQLite-based persistence for users and test results

---

## Main Features

- **Live sensor integration**
  - Connects to a Phyphox device through a user-provided URL
  - Reads accelerometer and gyroscope buffers in real time

- **Guided walking test**
  - Fixed-duration acquisition workflow
  - Live countdown and signal preview during measurement

- **Feature extraction pipeline**
  - Signal preprocessing
  - Gait-related feature generation
  - Biomechanical and clinical metric derivation

- **ML inference**
  - Loads a trained model from `model/cipn_final_model.pkl`
  - Computes a final CIPN probability score

- **Clinical dashboard**
  - Displays latest risk score
  - Shows derived metrics and historical test results

- **Persistence**
  - Stores all completed tests in `app.db`

---

## Tech Stack

- **Backend:** Flask
- **Frontend:** Jinja templates + HTML/CSS + Chart.js
- **Database:** SQLite
- **ML / Data:** NumPy, Pandas, SciPy, Joblib
- **Device acquisition:** Phyphox HTTP API

---

## Project Structure
```text
.
├── app.py
├── init_db.py
├── requirements.txt
├── LICENSE
├── app.db                     # generated locally, not intended for Git tracking
├── model/
│   └── cipn_final_model.pkl
├── src/
│   ├── bio_math.py
│   ├── clinical_metrics.py
│   ├── create_features.py
│   └── pedictor_din.py
├── static/
│   └── style.css
└── templates/
    ├── index.html
    ├── landing.html
    ├── layout.html
    ├── statistics.html
    ├── test.html
    └── video_pitch.webm
```


## Quickstart

This project is a Flask web application for live gait acquisition using a smartphone running **Phyphox**, followed by feature extraction, ML inference, and storage of results in a local SQLite database.

### 1. Setup and run

```bash
# Clone the repository
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>

# Create a virtual environment (isolates dependencies)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure the trained model exists at:
model/cipn_final_model.pkl

# Initialize the database (creates app.db locally)
python init_db.py

# Run the web application
python app.py
```
### Phyphox usage

To stream live IMU data to the application, open the **Phyphox** app on your smartphone and create a new experiment by pressing **"+"** and then **"Create Experiment"**. Add the **Accelerometer** and **Gyroscope** sensors, and set the **refresh rate to 0 Hz**. Then enable **Remote Access** in Phyphox. Once remote access is enabled, the app will provide a URL that must be used in this project as the device connection URL.