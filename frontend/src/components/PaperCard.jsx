import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios' // This uses the same axios instance
import './PaperCard.css'

function PaperCard({ paper, user, onUpdate }) {
  const [rating, setRating] = useState(0)
  const [similarPapers, setSimilarPapers] = useState([])
  const [showSimilar, setShowSimilar] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

 useEffect(() => {
  console.log('PaperCard mounted for paper:', paper.id)
  console.log(' Axios defaults:', {
    baseURL: axios.defaults.baseURL,
    authHeader: axios.defaults.headers.common['Authorization']
  })
  fetchUserRating()
}, [paper.id])
 const fetchUserRating = async () => {
  try {
    setIsLoading(true);
    console.log(` Fetching rating for paper ${paper.id}...`);
    
    const response = await axios.get(`/papers/${paper.id}/ratings/me`);
    
    console.log(` GET /ratings/me response:`, response.data);
    
    // Response should be {"rating": X}
    if (response.data && typeof response.data.rating === 'number') {
      setRating(response.data.rating);
      console.log(`Rating set to: ${response.data.rating}`);
    } else {
      console.warn(`Unexpected response format:`, response.data);
      setRating(0);
    }
    
  } catch (error) {
    console.error(`Error fetching rating:`, error.response?.data || error.message);
    setRating(0);
  } finally {
    setIsLoading(false);
  }
};

 const handleRating = async (value) => {
  console.log(" START RATING");
  console.log(`Paper ID: ${paper.id}`);
  console.log(`Rating value: ${value}`);
  
  try {
    console.log("📡 Sending POST request...");
    
    const response = await axios.post(`/papers/${paper.id}/ratings`, 
      { rating: value }
    );
    
    console.log("Backend response:", response.data);
    
  
    let result = response.data;
    
    // If response is an array, take first element
    if (Array.isArray(result)) {
      console.warn(" Backend returned array instead of object");
      result = result[0] || {};
    }
    
    console.log("Parsed result:", result);
    console.log("Message:", result.message);
    console.log("Rating value:", result.rating);
    
    if (result.success && result.rating) {
      // Update state with the rating from backend
      setRating(result.rating);
      console.log(" Local state updated to:", result.rating);
      
      // Show success
      alert(`Success: ${result.message}`);
    } else {
      console.warn(" Backend didn't return success");
      // Still update UI optimistically
      setRating(value);
    }
    
  } catch (error) {
    console.error(" Error:", error.response?.data || error.message);
    alert("Failed to save rating");
  }
  
  console.log("===== END RATING =====");
};

  const fetchSimilarPapers = async () => {
    if (similarPapers.length > 0) {
      setShowSimilar(!showSimilar)
      return
    }

    try {
      const response = await axios.get(`/papers/${paper.id}/similar`)
      setSimilarPapers(response.data)
      setShowSimilar(true)
    } catch (error) {
      console.error('Error fetching similar papers:', error)
    }
  }
  const handleTitleClick = () => {
    // If a DOI/URL is present, go directly to the original paper
    if (paper.doi) {
      const doi = paper.doi
      const url = doi.startsWith('http') ? doi : `https://doi.org/${doi}`
      window.open(url, '_blank', 'noopener,noreferrer')
      return
    }
    // Fallback: open internal detail page
    navigate(`/papers/${paper.id}`)
  }

  return (
    <div className="paper-card">
      <h3
        className="paper-title clickable"
        onClick={handleTitleClick}
      >
        {paper.title}
      </h3>
      <p className="paper-authors">{paper.authors}</p>
      <p className="paper-abstract">{paper.abstract}</p>
      
      <div className="paper-actions">
        <div className="rating">
          <span>Rate: </span>
          <div className="stars">
            {[1, 2, 3, 4, 5].map((value) => (
              <span
                key={value}
                className={`star ${value <= rating ? '' : 'empty'}`}
                onClick={() => handleRating(value)}
              >
                ★
              </span>
            ))}
          </div>
        </div>
        
        <button
          onClick={fetchSimilarPapers}
          className="btn btn-secondary btn-sm"
        >
          {showSimilar ? 'Hide' : 'Find'} Similar Papers
        </button>
      </div>

      {showSimilar && similarPapers.length > 0 && (
        <div className="similar-papers">
          <h4>Similar Papers:</h4>
          {similarPapers.map((similar) => (
            <div key={similar.id} className="similar-paper">
              <strong>{similar.title}</strong>
              <span className="similar-authors">{similar.authors}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default PaperCard




