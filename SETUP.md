# Quick Setup Guide

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ and npm installed

## Step 1: Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Start the backend server:
```bash
# Windows
start_backend.bat

# Linux/Mac
chmod +x start_backend.sh
./start_backend.sh

# Or manually:
cd backend
python main.py
```

The backend will run on `http://localhost:8000`

## Step 2: Frontend Setup

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the frontend development server:
```bash
# Windows
start_frontend.bat

# Linux/Mac
chmod +x start_frontend.sh
./start_frontend.sh

# Or manually:
cd frontend
npm run dev
```

The frontend will run on `http://localhost:3000`

## Step 3: Access the Application

1. Open your browser and go to `http://localhost:3000`
2. Register a new account
3. Start using the platform!

## Creating an Admin User

To create an admin user, you can either:

1. Register through the UI and manually update the database:
```python
# In Python shell or script
from backend.database import SessionLocal
from backend.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

user = db.query(User).filter(User.email == "your-email@example.com").first()
if user:
    user.is_admin = True
    db.commit()
```

2. Or modify the registration endpoint temporarily to allow admin registration

## Troubleshooting

### Backend Issues
- Make sure port 8000 is not in use
- Check that all Python dependencies are installed
- Verify SQLite database file is created in the backend directory

### Frontend Issues
- Make sure port 3000 is not in use
- Clear browser cache if you see old versions
- Check browser console for errors
- Ensure backend is running before starting frontend

### Database Reset
To reset the database, delete `backend/papers.db` and restart the backend server.




