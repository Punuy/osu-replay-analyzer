# osu! Replay Analyzer

A web-based tool for analyzing osu! replay files to provide detailed insights about gameplay patterns and timing statistics.

## Features

- Upload and analyze osu! replay files (.osr)
- Analyze note hit durations and timing patterns
- Generate visual distributions of hit timings
- Support for both regular notes and long notes (LN)
- Dark theme interface
- Interactive histogram visualization
- Statistical analysis including:
  - Total key presses
  - Average press duration
  - Minimum and maximum press times

## Requirements

- Python 3.10+
- FastAPI
- osrparse
- numpy
- matplotlib
- Additional dependencies listed in `requirements.txt`

## Installation

1. Clone this repository:
```bash
git clone [your-repository-url]
cd osu-replay-analyzer
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
uvicorn app.main:app --reload
```

2. Open your web browser and navigate to `http://localhost:8000`

3. Upload your osu! replay file (.osr) and corresponding beatmap file (.osu)

4. View the analysis results including:
   - Note hit duration distribution graph
   - Statistical metrics
   - Timing analysis

## Project Structure

```
osu-replay-analyzer/
├── app/
│   └── main.py          # FastAPI application and analysis logic
├── static/
│   ├── script.js        # Frontend JavaScript
│   └── style.css        # CSS styles
├── templates/
│   └── index.html       # Main webpage template
└── requirements.txt     # Python dependencies
```

## Credits

- osrparse library for osu! replay parsing
- FastAPI framework for the web server
- Matplotlib for data visualization
