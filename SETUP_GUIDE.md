# 🚀 Complete Setup Guide - Sleep Quality Predictor

Yeh guide step-by-step aapko FYP setup karna sikhayega! 🎓

## ✅ Checklist

- [ ] Ollama installed
- [ ] Python 3.8+ installed
- [ ] MySQL server running
- [ ] Project files downloaded
- [ ] Dependencies installed
- [ ] Database created
- [ ] App running successfully

---

## 📋 Step 1: Install Ollama (AI Engine)

### Windows/Mac/Linux:

1. Visit: **https://ollama.ai**
2. Download your OS version
3. Install the application
4. Open Terminal/Command Prompt

### Start Ollama:

```bash
ollama serve
```

Expected output:
```
Ollama is running on http://localhost:11434
```

⚠️ **Keep this terminal open!** (Background process)

---

## 🤖 Step 2: Download LLM Model

In a NEW terminal:

### Option A: Mistral (Recommended - Fast)
```bash
ollama pull mistral
```

### Option B: Llama2 (Better Quality - Slower)
```bash
ollama pull llama2
```

Model size: ~4-7GB (depends on model)

---

## 🐍 Step 3: Install Python & Dependencies

### Check Python Version:
```bash
python --version
# Should be 3.8 or higher
```

### If Not Installed:
- Download: https://www.python.org/downloads/
- Install (check "Add to PATH")

### Install Dependencies:
```bash
cd /path/to/sleep_ai_fyp

# Install all packages
pip install -r requirements.txt
```

Packages installed:
- Flask 3.0.3
- NumPy
- Scikit-learn
- MySQL Connector
- Requests

---

## 💾 Step 4: MySQL Database Setup

### Start MySQL:

**Windows:**
```bash
# MySQL Command Prompt or:
mysql -u root -p
```

**Mac/Linux:**
```bash
mysql -u root -p
```

### Run SQL Queries:

```sql
-- Create database
CREATE DATABASE sleep_ai_fyp_db;

-- Verify
SHOW DATABASES;
```

That's it — you don't need to manually create the `users` or `predictions` tables.
**`main_app.py` creates and migrates them automatically** every time it starts up
(see `init_db()`), so a fresh `sleep_ai_fyp_db` database is all you need.

For reference, the schema it creates is:

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

Note: Stress Level and Blood Pressure are no longer collected or stored.
If you're upgrading an older copy of this project, `init_db()` will try to
add the new columns to your existing `predictions` table automatically;
the old `stress`/`bp_upper`/`bp_lower` columns are simply left unused.

---

## 🔧 Step 5: Configure Database Connection

Edit `main_app.py`:

Find this section:
```python
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "haiderali962005"),  # Change if needed
    "database": os.environ.get("DB_NAME", "sleep_ai_fyp_db"),
}
```

You can either edit the default value directly, or (recommended) set an environment
variable before running the app so you never have to touch the code:

```bash
export DB_PASSWORD="YOUR_MYSQL_PASSWORD"
```

Also set a real secret key for session security in production:
```bash
export SECRET_KEY="a-long-random-string"
```

---

## 🚀 Step 6: Run Application

### Terminal 1 (Ollama - Keep Running):
```bash
ollama serve
```

### Terminal 2 (Flask App):
```bash
cd /path/to/sleep_ai_fyp
python main_app.py
```

Expected output:
```
✅ Database connected successfully!
✅ Models loaded successfully!
 * Running on http://127.0.0.1:5000
```

---

## 🌐 Step 7: Access Application

Open browser:
```
http://localhost:5000
```

You should see:
- **Login Page**: Shown first, with a "Register here" link below it
- **Register Page**: Create an account with username, age, email, phone, and password
- **Dashboard**: Shown automatically after a successful login
- **Beautiful UI**: Modern glassmorphism design with a dark mode toggle

---

## ✨ Step 8: Test Application

1. Register a new account (username, age, email, phone number, password).
2. Log in with that account — you'll land on the Dashboard.
3. Open **Home** from the navbar and fill the form with sample data:
   - Age: 25
   - Sleep Hours: 7
   - Screen Time: 8
   - Caffeine Intake: 2
   - Physical Activity: 5

4. Click "Analyze My Sleep"

5. Wait for analysis...

6. See your unified sleep score, status, AI analysis, and recommendations!

---

## 🔍 Verification Checklist

✅ **Ollama Running:**
- Terminal shows "Running on http://localhost:11434"
- Model is downloaded

✅ **Python Setup:**
```bash
python --version  # 3.8+
pip show Flask    # 3.0.3
```

✅ **MySQL Connection:**
```bash
mysql -u root -p
# Should connect successfully
```

✅ **App Running:**
- http://localhost:5000 opens
- All pages load
- Form submits successfully

---

## ⚙️ Configuration Options

### Change Model:

Edit `main_app.py`:
```python
OLLAMA_MODEL = "mistral"  # or "llama2"
```

### Change Temperature (Creativity):

```python
"temperature": 0.7  # 0.0 (deterministic) to 1.0 (creative)
```

### Change Port:

```python
app.run(debug=True, port=5001)  # Change 5000 to 5001
```

---

## 🐛 Common Issues & Solutions

### ❌ "Ollama service available nahi hai"

**Solution:**
```bash
# Terminal 1: Make sure Ollama is running
ollama serve

# Terminal 2: Check if port 11434 is accessible
curl http://localhost:11434
```

### ❌ "Database connection error"

**Solution:**
```bash
# Check MySQL is running
mysql -u root -p

# Verify database exists
SHOW DATABASES;

# Check credentials in main_app.py
```

### ❌ "Flask version error"

**Solution:**
```bash
pip install --upgrade Flask
pip install --upgrade Werkzeug
```

### ❌ "Model loading error"

**Solution:**
```bash
# Retrain models
python train_models.py

# Or check files exist:
# - sleep_models_v3.pkl
# - label_encoder_v3.pkl
```

### ❌ "Slow predictions"

**Solutions:**
1. Use faster model: `ollama pull mistral`
2. Lower temperature value
3. Increase RAM available
4. Close other applications

---

## 📱 Testing on Mobile

1. Find your PC IP:
   - Windows: `ipconfig` (look for IPv4)
   - Mac/Linux: `ifconfig` (look for inet)

2. On mobile browser:
   ```
   http://YOUR_IP:5000
   ```

3. Test responsive design

---

## 🎯 Next Steps

1. **Customize UI**: Edit `static/style.css`
2. **Add Features**: Extend `main_app.py`
3. **Deploy**: Use Heroku, PythonAnywhere, etc.
4. **Export Data**: Add CSV export feature
5. **Mobile App**: Create React Native version

---

## 📊 Project Statistics

- **5 ML Models**: For accurate predictions
- **Local AI**: Privacy-first approach
- **Modern UI**: Beautiful & responsive
- **Full-Stack**: Backend + Frontend
- **Production-Ready**: Error handling & logging

---

## 🎓 Learning Outcomes

This project teaches:
- ✅ Flask Web Development
- ✅ Machine Learning Ensemble Methods
- ✅ AI/LLM Integration
- ✅ Database Management
- ✅ Modern Frontend Design
- ✅ Full-Stack Development
- ✅ API Development

---

## 📞 Getting Help

1. **Check logs**: Terminal output
2. **Verify setup**: Recheck each step
3. **Check ports**: Make sure ports are free
4. **Update packages**: `pip install --upgrade -r requirements.txt`

---

## 🎉 Success!

Agar sab kuch work kar raha hai:
- ✅ App loading
- ✅ Predictions working
- ✅ Recommendations showing
- ✅ Data saving

**Congratulations!** Your FYP is ready! 🚀

---

**Happy Analyzing!** 😴✨

Made with ❤️ for better sleep quality!
