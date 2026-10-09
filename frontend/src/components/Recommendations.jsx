import React, { useState, useEffect } from 'react'
import axios from 'axios'
import PaperCard from './PaperCard'
import './Recommendations.css'

function Recommendations({ user }) {
  <button onClick={() => fetchRecommendations()} style={{margin: '10px'}}>
  🔄 Refresh Recommendations
  </button>
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRecommendations()
  }, [])

  const fetchRecommendations = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token') || ''
      const response = await axios.get('/recommendations?limit=20', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      console.log('Recommendations data:', response.data)
      
      setRecommendations(response.data)
    } catch (error) {
      console.error('Error fetching recommendations:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="recommendations-header">
        <h1>Recommended Papers</h1>
        <p>Based on your interests and ratings</p>
        <button onClick={fetchRecommendations} className="refresh-btn">
          Refresh Recommendations
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading recommendations...</div>
      ) : (
        <>
          {recommendations.length === 0 ? (
            <div className="card">
              <p className="empty-state">
                No recommendations yet. Rate some papers to get personalized recommendations!
              </p>
            </div>
          ) : (
            <div className="recommendations-grid">
              {recommendations.map((rec, index) => {
                // Create paper object from backend response
                const paper = {
                  id: rec.paper_id,        // Changed from rec.paper.id
                  title: rec.title,        // Changed from rec.paper.title
                  authors: rec.authors,    // Changed from rec.paper.authors
                  abstract: rec.abstract,  // Changed from rec.paper.abstract
                  doi: rec.doi || null,
                  created_at: rec.created_at || new Date().toISOString(),
                  views: rec.views || 0,
                  uploaded_by: rec.uploaded_by || user?.id
                }
                
                return (
                  <div key={paper.id || index} className="recommendation-card">
                    <PaperCard paper={paper} user={user} onUpdate={fetchRecommendations} />
                    <div className="recommendation-meta">
                      <div className="recommendation-score">
                        Match Score: {rec.score ? (rec.score * 100).toFixed(1) + '%' : 'N/A'}
                      </div>
                      <div className="recommendation-reason">{rec.reason || 'Recommended for you'}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default Recommendations