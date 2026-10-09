// frontend/src/App.js - SET THIS AT THE VERY TOP
import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'

// ✅ SET AXIOS DEFAULTS IMMEDIATELY
axios.defaults.baseURL = 'http://localhost:8000'

// Check if token exists in localStorage and set it
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

// Now import other components
import Login from './components/Login'
import Register from './components/Register'
import Dashboard from './components/Dashboard'
import PaperList from './components/PaperList'
import PaperUpload from './components/PaperUpload'
import Recommendations from './components/Recommendations'
import AdminDashboard from './components/AdminDashboard'
import PaperDetail from './components/PaperDetail'
import Navbar from './components/Navbar'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Token is already set above, now fetch user
    if (token) {
      fetchUser()
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async () => {
    try {
      const response = await axios.get('/users/me')
      setUser(response.data)
    } catch (error) {
      // Token invalid, clear it
      localStorage.removeItem('token')
      delete axios.defaults.headers.common['Authorization']
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = (token) => {
    localStorage.setItem('token', token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    fetchUser()
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
    setUser(null)
  }

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <Router>
      <div className="App">
        {user && <Navbar user={user} onLogout={handleLogout} />}
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />}
          />
          <Route
            path="/register"
            element={user ? <Navigate to="/dashboard" /> : <Register onLogin={handleLogin} />}
          />
          <Route
            path="/dashboard"
            element={user ? <Dashboard user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/papers"
            element={user ? <PaperList user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/papers/:id"
            element={user ? <PaperDetail user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/upload"
            element={user ? <PaperUpload user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/recommendations"
            element={user ? <Recommendations user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/admin"
            element={user?.is_admin ? <AdminDashboard user={user} /> : <Navigate to="/dashboard" />}
          />
          <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App