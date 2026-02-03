# 🌡️ LCZ-HeatMoist

**Interactive Visualization of Urban Heat, Moisture, and Dry Islands Across 50 US Cities**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 Overview

**LCZ-HeatMoist** is an interactive web application for exploring the relationships between Local Climate Zones (LCZ) and urban climate phenomena including:

- **SUHI (Surface Urban Heat Island)** - Temperature differences between urban and rural areas
- **UMI (Urban Moisture Island)** - Humidity variations in urban environments  
- **UDI (Urban Dry Island)** - Moisture deficit in highly urbanized areas

The app provides comprehensive analysis of 50 major US cities from 2000-2020, enabling researchers, urban planners, and climate scientists to understand how urban morphology influences local climate conditions.

![App Screenshot](docs/screenshot.png)

## 🔬 Scientific Background

### What are Local Climate Zones (LCZ)?

Local Climate Zones are a classification system for urban and rural areas based on their physical properties. The LCZ scheme divides landscapes into 17 classes:

| Built Types (1-10) | Land Cover Types (11-17) |
|-------------------|-------------------------|
| 1. Compact high-rise | 11. Dense trees |
| 2. Compact mid-rise | 12. Scattered trees |
| 3. Compact low-rise | 13. Bush, scrub |
| 4. Open high-rise | 14. Low plants |
| 5. Open mid-rise | 15. Bare rock/paved |
| 6. Open low-rise | 16. Bare soil/sand |
| 7. Lightweight low-rise | 17. Water |
| 8. Large low-rise | |
| 9. Sparsely built | |
| 10. Heavy industry | |

### Key Metrics

- **SUHI = T_urban - T_rural**: Positive values indicate urban areas are warmer
- **UMI = H_urban - H_rural**: Positive values indicate urban areas are more humid
- **UDI = -UMI**: Positive values indicate urban areas are drier

## ✨ Features

### 🗺️ CONUS Explorer
- Interactive map of all 50 cities
- Regional filtering (Northeast, Midwest, South, West)
- City-level SUHI/UMI/UDI metrics

### 🏙️ City Explorer
- Deep-dive analysis for individual cities
- Temporal trends (2000-2020)
- Seasonal patterns (Spring, Summer, Fall, Winter)
- Day/Night comparisons

### 📊 City Comparison
- Side-by-side comparison of multiple cities
- Ranking charts
- Radar plots for multi-metric comparison

### 🏘️ LCZ Analysis
- Analysis by Local Climate Zone class
- LCZ composition visualization
- SUHI-UMI coupling analysis

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aashish66/Unravel_UHI_UMI_UDI.git
   cd Unravel_UHI_UMI_UDI
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser:**
   Navigate to `http://localhost:8501`

## 📁 Project Structure

```
LCZ-HeatMoist/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── pages/                 # Multi-page app pages
│   ├── 1_🗺️_CONUS_Explorer.py
│   ├── 2_🏙️_City_Explorer.py
│   ├── 3_📊_City_Comparison.py
│   └── 4_🏘️_LCZ_Analysis.py
├── utils/                 # Utility modules
│   ├── data_loader.py     # S3 data loading functions
│   ├── chart_utils.py     # Plotly chart generators
│   └── map_utils.py       # Folium map utilities
└── README.md
```

## 📊 Data Sources

The application uses the following data:

| Data Type | Source | Resolution |
|-----------|--------|------------|
| Land Surface Temperature | MODIS LST | 1 km |
| Humidity | ERA5-Land | 1 km |
| LCZ Classification | WUDAPT | 100 m |
| City Boundaries | US Census | Vector |

Data is hosted on AWS S3 for fast, reliable access.

## 🛠️ Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Visualization**: [Plotly](https://plotly.com/), [Folium](https://python-visualization.github.io/folium/)
- **Geospatial**: [GeoPandas](https://geopandas.org/), [xarray](https://xarray.pydata.org/)
- **Data Storage**: AWS S3
- **Deployment**: Streamlit Cloud

## 📈 Example Use Cases

1. **Urban Planning**: Identify which LCZ types contribute most to urban heat islands
2. **Climate Research**: Analyze seasonal and temporal trends in SUHI/UMI
3. **Policy Making**: Compare cities to understand successful heat mitigation strategies
4. **Education**: Learn about urban climate phenomena interactively

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Aashish Gautam** - *Principal Investigator* - Jackson State University

## 🙏 Acknowledgments

- MODIS Science Team for Land Surface Temperature data
- ECMWF for ERA5-Land reanalysis data
- WUDAPT project for LCZ classification methodology
- Streamlit team for the excellent framework

## 📧 Contact

For questions or collaboration opportunities, please contact:
- Email: [your-email@jsu.edu]
- GitHub: [@aashish66](https://github.com/aashish66)

---

<p align="center">
  Made with ❤️ at Jackson State University
</p>
