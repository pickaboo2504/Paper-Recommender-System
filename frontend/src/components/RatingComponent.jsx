// frontend/src/components/Rating/SimpleRating.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SimpleRating = ({ paperId }) => {
  const [userRating, setUserRating] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Get current rating
  useEffect(() => {
    fetchUserRating();
  }, [paperId]);

  const fetchUserRating = async () => {
  try {
    const token = localStorage.getItem('token');
    
    // CHECK IF TOKEN EXISTS
    if (!token) {
      console.log("No token found, user might not be logged in");
      setUserRating(0);
      return;
    }
    
    console.log("Token found, fetching rating...");
    
    const response = await axios.get(`http://localhost:8000/papers/${paperId}/ratings/me`, {
      headers: { 
        Authorization: `Bearer ${token}`  
      }
    });
    
    console.log("Current rating response:", response.data);
    setUserRating(response.data.rating || 0);
    
  } catch (error) {
    console.error("Error getting rating:", error);
    setUserRating(0);
  }
};

  
  const ratePaper = async (rating) => {
    console.log("RATE PAPER CALLED! Rating:", rating, "Paper ID:", paperId);
    
    if (loading) return;
    
    setLoading(true);
    setMessage('');

    try {
      const token = localStorage.getItem('token');
      console.log("Token exists:", !!token);
      
      if (!token) {
        setMessage('Please login to rate papers');
        setLoading(false);
        return;
      }

      console.log("Sending request to backend...");
      
      const response = await axios.post(
        `http://localhost:8000/papers/${paperId}/ratings`,
        { rating: rating },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log("✅ Response from backend:", response.data);
      
      setUserRating(rating);
      setMessage(`Rated ${rating} stars!`);
      
      // Clear message after 2 seconds
      setTimeout(() => setMessage(''), 2000);

    } catch (error) {
      console.error("❌ Error:", error.response?.data || error.message);
      setMessage(error.response?.data?.detail || 'Failed to save rating');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      padding: '20px',
      border: '1px solid #ddd',
      borderRadius: '8px',
      margin: '20px 0',
      background: '#f9f9f9'
    }}>
      <h3 style={{ margin: '0 0 15px 0' }}>Rate This Paper</h3>
      
      <div style={{ marginBottom: '15px' }}>
        <p>Your current rating: <strong>{userRating > 0 ? `${userRating} stars` : 'Not rated yet'}</strong></p>
      </div>
      
      {/* SIMPLE BUTTONS THAT WILL DEFINITELY WORK */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <button
          onClick={() => ratePaper(1)}
          disabled={loading}
          style={{
            padding: '10px 15px',
            background: '#FF6B6B',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ★ 1 Star
        </button>
        
        <button
          onClick={() => ratePaper(2)}
          disabled={loading}
          style={{
            padding: '10px 15px',
            background: '#FFA726',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ★★ 2 Stars
        </button>
        
        <button
          onClick={() => ratePaper(3)}
          disabled={loading}
          style={{
            padding: '10px 15px',
            background: '#FFCA28',
            color: '333',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ★★★ 3 Stars
        </button>
        
        <button
          onClick={() => ratePaper(4)}
          disabled={loading}
          style={{
            padding: '10px 15px',
            background: '#66BB6A',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ★★★★ 4 Stars
        </button>
        
        <button
          onClick={() => ratePaper(5)}
          disabled={loading}
          style={{
            padding: '10px 15px',
            background: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ★★★★★ 5 Stars
        </button>
      </div>
      
      {loading && (
        <div style={{ color: '#666', margin: '10px 0' }}>
          ⏳ Saving rating...
        </div>
      )}
      
      {message && (
        <div style={{
          padding: '10px',
          margin: '10px 0',
          background: message.includes('Failed') ? '#FFEBEE' : '#E8F5E9',
          color: message.includes('Failed') ? '#C62828' : '#2E7D32',
          borderRadius: '4px'
        }}>
          {message}
        </div>
      )}
      
      {/* DEBUG INFO */}
      <div style={{
        marginTop: '20px',
        padding: '10px',
        background: '#E3F2FD',
        borderRadius: '4px',
        fontSize: '12px',
        color: '#1565C0'
      }}>
        <strong>Debug Info:</strong>
        <div>Paper ID: {paperId}</div>
        <div>Current Rating: {userRating}</div>
        <div>Loading: {loading ? 'Yes' : 'No'}</div>
        <div>Token: {localStorage.getItem('token') ? 'Exists' : 'Missing'}</div>
      </div>
    </div>
  );
};

export default SimpleRating;