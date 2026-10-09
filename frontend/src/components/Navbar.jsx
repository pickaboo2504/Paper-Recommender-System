import React from 'react'
import { Link } from 'react-router-dom'
import './Navbar.css'

function Navbar({ user, onLogout }) {
  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/dashboard" className="nav-logo">
          📚 Paper Platform
        </Link>
        <div className="nav-links">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/papers">Papers</Link>
          <Link to="/upload">Upload</Link>
          <Link to="/recommendations">Recommendations</Link>
          {user?.is_admin && <Link to="/admin">Admin</Link>}
          <span className="nav-user">{user?.full_name}</span>
          <button onClick={onLogout} className="btn-logout">Logout</button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar




