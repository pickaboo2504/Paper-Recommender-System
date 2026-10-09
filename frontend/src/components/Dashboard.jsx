import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import './Dashboard.css'

function Dashboard({ user }) {
  const [fields, setFields] = useState([])
  const [newField, setNewField] = useState('')
  const [recentPapers, setRecentPapers] = useState([])

  useEffect(() => {
    fetchFields()
    fetchRecentPapers()
  }, [])

  const fetchFields = async () => {
    try {
      const response = await axios.get('/users/fields')
      setFields(response.data)
    } catch (error) {
      console.error('Error fetching fields:', error)
    }
  }

  const fetchRecentPapers = async () => {
    try {
      const response = await axios.get('/papers?limit=5')
      setRecentPapers(response.data)
    } catch (error) {
      console.error('Error fetching papers:', error)
    }
  }

  const addField = async (e) => {
    e.preventDefault()
    if (!newField.trim()) return

    try {
      await axios.post('/users/fields', { field_name: newField })
      setNewField('')
      fetchFields()
    } catch (error) {
      console.error('Error adding field:', error)
    }
  }

  return (
    <div className="container">
      <div className="dashboard-header">
        <h1>Welcome, {user.full_name}!</h1>
        <p>Manage your research interests and discover new papers</p>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h2>Your Fields</h2>
          <form onSubmit={addField} className="field-form">
            <input
              type="text"
              placeholder="Add a field (e.g., Machine Learning, Biology)"
              value={newField}
              onChange={(e) => setNewField(e.target.value)}
              className="input"
            />
            <button type="submit" className="btn btn-primary">Add Field</button>
          </form>
          <div className="fields-list">
            {fields.map((field) => (
              <span key={field.id} className="field-tag">{field.field_name}</span>
            ))}
            {fields.length === 0 && <p className="empty-state">No fields added yet</p>}
          </div>
        </div>

        <div className="card">
          <h2>Quick Actions</h2>
          <div className="quick-actions">
            <Link to="/upload" className="action-btn">
              📄 Upload Paper
            </Link>
            <Link to="/recommendations" className="action-btn">
              🔍 Get Recommendations
            </Link>
            <Link to="/papers" className="action-btn">
              📚 Browse Papers
            </Link>
          </div>
        </div>

        <div className="card">
          <h2>Recent Papers</h2>
          <div className="recent-papers">
            {recentPapers.map((paper) => (
              <Link key={paper.id} to={`/papers`} className="recent-paper">
                <div className="recent-paper-title">{paper.title}</div>
                <div className="recent-paper-authors">{paper.authors}</div>
              </Link>
            ))}
            {recentPapers.length === 0 && <p className="empty-state">No papers yet</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard




