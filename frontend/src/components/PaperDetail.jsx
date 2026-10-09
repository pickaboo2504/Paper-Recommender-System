import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import PaperCard from './PaperCard'
import './PaperDetail.css'
import SimpleRating from './RatingComponent';


function PaperDetail({ user }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [paper, setPaper] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchPaper = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await axios.get(`/papers/${id}`)
        setPaper(response.data)
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load paper')
      } finally {
        setLoading(false)
      }
    }

    fetchPaper()
  }, [id])

  const handleBack = () => {
    navigate('/papers')
  }
  

  const handleOpenPdf = () => {
    if (!paper?.file_path) return
    window.open(`/papers/${paper.id}/file`, '_blank', 'noopener,noreferrer')
  }

  if (loading) {
    return <div className="container"><div className="loading">Loading paper...</div></div>
  }

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <p className="error">{error}</p>
          <button className="btn btn-secondary" onClick={handleBack}>
            Back to Papers
          </button>
        </div>
      </div>
    )
  }

  if (!paper) {
    return (
      <div className="container">
        <div className="card">
          <p className="empty-state">Paper not found</p>
          <button className="btn btn-secondary" onClick={handleBack}>
            Back to Papers
          </button>
        </div>
      </div>
    )
  }
  const handleRatingSuccess = (newRating) => {
    setPaper(prev => ({
      ...prev,
      user_rating: newRating
    }));
    // Force refresh
    fetchPaperDetails();
  };



  return (
    <div className="container">
      <div className="paper-detail-header">
        <button className="btn btn-secondary" onClick={handleBack}>
          ← Back
        </button>
      </div>

      <div className="card paper-detail-card">
        <h1 className="paper-detail-title">{paper.title}</h1>
        <p className="paper-detail-authors">{paper.authors}</p>
         <SimpleRating paperId={paperId} />

        {paper.doi && (
          <div className="paper-detail-doi">
            <span>DOI: </span>
            <a
              href={paper.doi.startsWith('http') ? paper.doi : `https://doi.org/${paper.doi}`}
              target="_blank"
              rel="noreferrer"
            >
              {paper.doi}
            </a>
          </div>
        )}

        {paper.tags && paper.tags.length > 0 && (
          <div className="tags">
            {paper.tags.map((tag) => (
              <span key={tag} className="tag">
                {tag}
              </span>
            ))}
          </div>
        )}

        <h3 className="paper-detail-section-title">Abstract</h3>
        <p className="paper-detail-abstract">{paper.abstract}</p>

        {paper.file_path && (
          <div className="paper-detail-file">
            <button className="btn btn-primary" onClick={handleOpenPdf}>
              Open PDF
            </button>
          </div>
        )}
      </div>

      {/* Reuse PaperCard for rating + similar papers UX */}
      <div className="paper-detail-rating">
        <PaperCard paper={paper} user={user} />
      </div>
    </div>
  )
}

export default PaperDetail


