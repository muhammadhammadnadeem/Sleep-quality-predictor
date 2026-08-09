# Sleep Quality Predictor - AI-Powered FYP

An AI-powered application that analyzes sleep-related lifestyle habits and returns one clear,
unified sleep quality prediction with a numeric score, an AI-generated analysis, and
personalized recommendations.

## Features

**Authentication**
- Secure registration (username, age, email, phone, password) and login
- Passwords are hashed with Werkzeug's `generate_password_hash`
- Session-based login; the app opens on the Login page, with a "Register here" link

**Unified AI Prediction**
- An internal ensemble of 5 ML algorithms (Logistic Regression, Decision Tree, Random Forest,
  KNN, Naive Bayes) votes on a prediction — but only ONE final result is ever shown to the user
- A deterministic 0-100 sleep quality score, consistent with the predicted status
- A rule-based AI analysis engine that explains which factors are helping or hurting sleep
- Personalized recommendations, optionally enriched by a local LLM (Ollama), with an automatic
  rule-based fallback if Ollama isn't running

**Modern UI/UX**
- Glassmorphism design with floating gradient orbs for subtle depth
- Full dark mode support (toggle button, every page)
- Responsive layout (mobile & desktop) with smooth animations and transitions
- No emojis — clean inline SVG icons throughout

**Data Management**
- Per-user prediction history tracking
- Statistics dashboard (total predictions, avg sleep hours, good sleep days, avg score)
- Database storage (MySQL), auto-created and auto-migrated on startup

**Privacy & Security**
- All prediction processing happens locally
- No cloud API calls required
- Each user only ever sees their own history

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask (Python) |
| **Auth** | Flask sessions + Werkzeug password hashing |
| **ML Framework** | Scikit-learn, NumPy |
| **AI/LLM** | Ollama (Local, optional) |
| **Database** | MySQL |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Visualization** | Chart.js |

## Input Parameters

The predictor analyzes 5 key factors:

1. **Age** (years)
2. **Sleep Hours** (per night)
3. **Screen Time** (hours/day)
4. **Caffeine Intake** (cups/day)
5. **Physical Activity** (hours/week)

> Stress Level and Blood Pressure have been removed from the input form, prediction
> pipeline, and database schema.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MySQL Server
- Ollama (Download from https://ollama.ai)
- 4GB+ RAM recommended

### Step 1: Install Ollama

```bash
# Download from https://ollama.ai
# Install the application
# Run in terminal:
ollama serve
```

Pull your preferred model:
```bash
ollama pull mistral    # Recommended - fast & good quality
# OR
ollama pull llama2     # Better quality but slower
```

### Step 2: Setup Database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE sleep_ai_fyp_db;
```

That's it — `main_app.py` automatically creates (and best-effort migrates) the `users` and
`predictions` tables the first time it starts, via `init_db()`. For reference:

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    age INT,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    age FLOAT,
    sleep_hours FLOAT,
    screen_time FLOAT,
    caffeine FLOAT,
    physical FLOAT,
    sleep_score FLOAT,
    final_prediction VARCHAR(20),
    ai_analysis LONGTEXT,
    recommendations LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Step 3: Install Python Dependencies

```bash
# Navigate to project directory
cd sleep_ai_fyp

# Install requirements
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python main_app.py
```

Visit: `http://localhost:5000`

## 📂 Project Structure

```
sleep_ai_fyp/
├── main_app.py              # Flask application (auth + prediction + AI analysis)
├── requirements.txt         # Python dependencies
├── sleep_models_v3.pkl      # Trained ML models (5-feature schema)
├── label_encoder_v3.pkl     # Label encoder
├── train_models.py          # Model training script
├── templates/
│   ├── base.html           # Base template (navbar, dark mode toggle)
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── index.html          # Home page (prediction form)
│   ├── result.html         # Unified results page
│   ├── visualize.html      # Sleep score trend chart
│   ├── dashboard.html      # Dashboard (stats + history)
│   └── about.html          # About page
└── static/
    ├── style.css           # Styling (light + dark mode)
    └── script.js           # JavaScript utilities (theme toggle, nav)
```

## 🔧 Configuration

### Change LLM Model

Edit `main_app.py`:
```python
OLLAMA_MODEL = "mistral"  # Change to "llama2" or other models
```

### Adjust LLM Temperature

Lower = deterministic, Higher = creative
```python
"temperature": 0.7  # Range: 0.0 - 1.0
```

### Database Connection

Set environment variables (recommended) or edit the defaults in `main_app.py`:
```bash
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="your_password"
export DB_NAME="sleep_ai_fyp_db"
export SECRET_KEY="a-long-random-string"
```

## 📊 How It Works

```
Login / Register
    ↓
User Input (5 lifestyle parameters)
    ↓
5 ML Models (internal ensemble, not shown individually)
    ↓
Majority Vote → Final Prediction
    ↓
Sleep Score Engine (0-100)
    ↓
AI Analysis Engine (factor-by-factor explanation)
    ↓
Recommendations (local LLM if available, rule-based fallback)
    ↓
Unified Result Display + Database Save
    ↓
History & Trend Analytics
```

## 🎯 Output Categories

| Category | Score | Color |
|----------|-------|-------|
| **Poor** | Low Quality | 🔴 Red |
| **Average** | Moderate Quality | 🟡 Yellow |
| **Good** | High Quality | 🟢 Green |

## 🐛 Troubleshooting

### "Ollama service available nahi hai"
```bash
# Make sure Ollama is running in another terminal
ollama serve
```

### Database Connection Error
```bash
# Check MySQL is running
mysql -u root -p
# Verify credentials in main_app.py
```

### Flask Version Error
```bash
# Update Flask
pip install --upgrade Flask
```

### Model Loading Error
```bash
# Ensure pickle files are in project directory
# Retrain models if corrupted
python train_models.py
```

## 📈 Performance Tips

1. **Faster Predictions**: Use `mistral` model
2. **Better Quality**: Use `llama2` model
3. **Lower Memory**: Reduce `temperature` value
4. **Faster UI**: Clear browser cache

## 🔒 Privacy Features

✅ No cloud API calls
✅ Local LLM processing
✅ Data stays on your machine
✅ No tracking or analytics
✅ Secure database storage

## 📱 Browser Support

| Browser | Status |
|---------|--------|
| Chrome | ✅ Fully Supported |
| Firefox | ✅ Fully Supported |
| Safari | ✅ Fully Supported |
| Edge | ✅ Fully Supported |
| Mobile | ✅ Responsive |

## 🎓 Educational Value

This project demonstrates:
- Machine Learning Ensemble Methods
- Flask Web Development
- AI/LLM Integration
- Database Management
- Modern Frontend Design
- Full-Stack Development

## 📝 Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Advanced analytics
- [ ] Export to PDF/CSV
- [ ] Social sharing
- [ ] Multi-language support
- [ ] Wearable device integration
- [ ] Real-time recommendations

## 📄 License

This project is created for educational purposes.

## 👨‍💻 Support

For issues or questions:
1. Check Troubleshooting section
2. Verify all dependencies installed
3. Ensure Ollama is running
4. Check database connection

## 🎉 Credits

Built with ❤️ as a Final Year Project

**Technologies:**
- Flask
- Scikit-learn
- Ollama
- Chart.js
- MySQL

---

**Made with ❤️ for better sleep quality!** 😴✨

Happy analyzing! 🚀
