// frontend/src/components/AdminDashboard.jsx
import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from 'recharts'
import './AdminDashboard.css'

function AdminDashboard({ user }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [data, setData] = useState({
    metrics: null,
    users: [],
    papers: [],
    activity: [],
    recommender: null
  })

  useEffect(() => {
    if (user?.is_admin) {
      fetchOverviewData()
    } else {
      setError('Admin access required')
      setLoading(false)
    }
  }, [user])

  const fetchOverviewData = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      
      // Fetch only overview data initially
      const response = await axios.get('/admin/metrics/overview', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      setData(prev => ({ ...prev, metrics: response.data }))
    } catch (err) {
      console.error('Admin error:', err)
      setError('Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }

  const fetchTabData = async (tab) => {
    try {
      const token = localStorage.getItem('token')
      let endpoint = ''
      
      switch(tab) {
        case 'users':
          endpoint = '/admin/metrics/users'
          break
        case 'papers':
          endpoint = '/admin/metrics/papers?limit=50'
          break
        case 'activity':
          endpoint = '/admin/metrics/activity?days=30'
          break
        case 'recommender':
          endpoint = '/admin/metrics/recommender'
          break
        default:
          return
      }
      
      const response = await axios.get(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      setData(prev => ({ ...prev, [tab]: response.data }))
    } catch (err) {
      console.error(`Error fetching ${tab}:`, err)
    }
  }

  const handleTabClick = (tab) => {
    setActiveTab(tab)
    if (!data[tab] || (Array.isArray(data[tab]) && data[tab].length === 0)) {
      fetchTabData(tab)
    }
  }

  const handleRebuildRecommender = async () => {
    try {
      const token = localStorage.getItem('token')
      await axios.post('/admin/metrics/rebuild-recommender', {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      alert('Recommender rebuilt successfully!')
      fetchTabData('recommender')
    } catch (err) {
      alert('Failed to rebuild recommender')
    }
  }

  if (loading) {
    return <div className="container"><div className="loading">Loading admin dashboard...</div></div>
  }

  if (error || !user?.is_admin) {
    return (
      <div className="container">
        <div className="error-card">
          <h2>🔒 Admin Access Required</h2>
          <p>You need administrator privileges to access this page.</p>
        </div>
      </div>
    )
  }

  // Prepare chart data
  const topTagsData = data.metrics?.top_tags?.map(tag => ({
    name: tag.name?.length > 15 ? tag.name.substring(0, 15) + '...' : tag.name || '',
    count: tag.count || 0
  })) || []

  const activityData = data.activity?.activity?.map(day => ({
    date: day.date,
    Papers: day.papers || 0,
    Ratings: day.ratings || 0,
    Users: day.users || 0
  })) || []

  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a']

  return (
    <div className="container">
      <div className="admin-header">
        <h1>📊 Admin Dashboard</h1>
        <p>Monitor platform metrics and activity</p>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        {['overview', 'users', 'papers', 'recommender'].map(tab => (
          <button
            key={tab}
            className={activeTab === tab ? 'active' : ''}
            onClick={() => handleTabClick(tab)}
          >
            {tab === 'overview' && '📈 Overview'}
            {tab === 'users' && '👥 Users'}
            {tab === 'papers' && '📄 Papers'}
            {tab === 'recommender' && '🤖 Recommender'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && data.metrics && (
          <>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{data.metrics.total_users || 0}</div>
                <div className="metric-label">Total Users</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.metrics.total_papers || 0}</div>
                <div className="metric-label">Total Papers</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.metrics.total_ratings || 0}</div>
                <div className="metric-label">Total Ratings</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.metrics.total_tags || 0}</div>
                <div className="metric-label">Total Tags</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.metrics.average_rating?.toFixed(2) || '0.00'}</div>
                <div className="metric-label">Avg Rating</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{data.metrics.recent_papers || 0}</div>
                <div className="metric-label">Recent Papers</div>
              </div>
            </div>

            {topTagsData.length > 0 && (
              <div className="card">
                <h2>Top Tags</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={topTagsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#667eea" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}

        {activeTab === 'users' && (
          <div className="card">
            <h2>Users ({data.users.length})</h2>
            <div className="table-container">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Email</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Papers</th>
                    <th>Ratings</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {data.users.map(u => (
                    <tr key={u.id}>
                      <td>{u.id}</td>
                      <td>{u.email}</td>
                      <td>{u.full_name}</td>
                      <td>{u.is_admin ? 'Admin' : 'User'}</td>
                      <td>{u.papers_count}</td>
                      <td>{u.ratings_count}</td>
                      <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'papers' && (
          <div className="card">
            <h2>Papers ({data.papers.length})</h2>
            <div className="table-container">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Authors</th>
                    <th>Uploader</th>
                    <th>Ratings</th>
                    <th>Avg Rating</th>
                    <th>Has File</th>
                  </tr>
                </thead>
                <tbody>
                  {data.papers.map(p => (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>{p.title}</td>
                      <td>{p.authors?.split(',')[0]}...</td>
                      <td>{p.uploaded_by}</td>
                      <td>{p.ratings_count}</td>
                      <td>{p.average_rating?.toFixed(1)}</td>
                      <td>{p.has_file ? '✅' : '❌'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'recommender' && data.recommender && (
          <div className="card">
            <h2>Recommender System</h2>
            <div className="recommender-stats">
              <p><strong>Papers in system:</strong> {data.recommender.papers_in_system}</p>
              <p><strong>Features built:</strong> {data.recommender.features_built ? '✅' : '❌'}</p>
              <p><strong>Last updated:</strong> {new Date(data.recommender.last_feature_update).toLocaleString()}</p>
              <button onClick={handleRebuildRecommender} className="btn-primary">
                🔄 Rebuild Recommender
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminDashboard