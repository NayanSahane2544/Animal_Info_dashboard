# 🌍 Planet Zoo: Interactive Biodiversity & Analytics Dashboard

An interactive, full-stack data analytics web application built with **Streamlit** and **Plotly** to visualize, compare, and analyze a curated dataset of ~275 animal species. 

## 🚀 Features

*   🦁 **Dynamic Animal Profiles:** View comprehensive biological statistics. The app dynamically changes its UI theme color based on the selected animal's natural color.
*   📍 **Geospatial Habitat Mapping:** Interactive Plotly Choropleth maps highlighting the specific countries and regions where the animal is found.
*   ⚖️ **Head-to-Head Comparison:** Select any two animals and compare their speed, weight, lifespan, and height using an interactive Radar Chart.
*   📈 **Global Analytics:** Logarithmic scatter plots (Weight vs. Height/Speed) and Top 10 Leaderboards for the fastest, heaviest, and longest-living animals.
*   🌳 **Evolutionary Tree:** A physics-based, interactive network graph mapping the relationships between biological families and specific species.
*   🔊 **Live API Integrations:** Automatically fetches real-time Wikipedia summaries and open-source animal audio recordings via the Xeno-canto API.
*   📄 **PDF Report Generation:** Click a button to dynamically generate and download a beautifully formatted PDF report of the selected animal.

## 🛠️ Tech Stack

*   **Frontend & Framework:** Streamlit
*   **Data Manipulation:** Pandas, NumPy
*   **Data Visualization:** Plotly (Express & Graph Objects), Pyvis (Network graphs)
*   **External APIs:** Wikipedia REST API, Xeno-canto Audio API
*   **Utilities:** FPDF (PDF Generation), Pillow (Image Processing)

## 💻 Local Setup & Installation

Follow these steps to run the dashboard locally on your machine.

**1. Clone the repository**
```bash
git clone [https://github.com/your-username/planet-zoo-dashboard.git](https://github.com/your-username/planet-zoo-dashboard.git)
cd planet-zoo-dashboard
```
**2. Create a Virtual Environment**
It is highly recommended to use a virtual environment (venv) to manage dependencies.


# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

**3. Install Dependencies**

pip install -r requirements.txt


**4. Add Images & Data**

Ensure your dataset is named dataset.csv and is placed in the root directory.

Create a folder named images/ in the root directory and add .jpg or .png images corresponding to the animal names (e.g., Lion.jpg).

**5. Run the Application**


streamlit run app.py


📂 Project Structure

*├── app.py                  # Main Streamlit application script
*├── dataset.csv             # Biological dataset of ~275 species
*├── requirements.txt        # Python package dependencies
*├── images/                 # Folder containing animal images
*└── README.md               # Project documentation


👨‍💻 Author
Nayan Sahane
