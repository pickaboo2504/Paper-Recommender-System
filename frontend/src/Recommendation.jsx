import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getRecommendations } from '../services/api';
import {
  Card,
  CardContent,
  Typography,
  Rating,
  Chip,
  Box,
  CircularProgress,
  Alert,
  Grid,
  Paper,
  Divider,
  IconButton
} from '@mui/material';
import { Link } from 'react-router-dom';
import VisibilityIcon from '@mui/icons-material/Visibility';
import TagIcon from '@mui/icons-material/Tag';

function Recommendations() {
  const { token } = useAuth();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (token) {
      fetchRecommendations();
    }
  }, [token]);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getRecommendations(token, 20);
      console.log('Recommendations data:', data); // Debug log
      
      // Make sure data is an array and has items
      if (Array.isArray(data)) {
        setRecommendations(data);
      } else {
        console.error('Expected array but got:', data);
        setRecommendations([]);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
      setError('Failed to load recommendations. Please try again.');
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    fetchRecommendations();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
        <Typography variant="body1" ml={2}>
          Loading recommendations...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
        <Box mt={1}>
          <button onClick={handleRefresh} style={{ marginRight: '10px' }}>
            Try Again
          </button>
        </Box>
      </Alert>
    );
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <Paper elevation={3} sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          No Recommendations Yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Rate some papers to get personalized recommendations!
        </Typography>
        <button onClick={handleRefresh}>
          Refresh
        </button>
      </Paper>
    );
  }

  return (
    <div>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Your Recommendations
        </Typography>
        <button onClick={handleRefresh}>
          Refresh Recommendations
        </button>
      </Box>

      <Grid container spacing={3}>
        {recommendations.map((rec, index) => {
          // Debug: Check what data we have
          console.log('Rendering recommendation:', index, rec);
          
          // Make sure rec exists and has required properties
          if (!rec) {
            console.warn('Undefined recommendation at index:', index);
            return null;
          }
          
          // Use rec.paper_id instead of rec.id if that's what your API returns
          const paperId = rec.paper_id || rec.id;
          const title = rec.title || 'Untitled Paper';
          const authors = rec.authors || 'Unknown Authors';
          const abstract = rec.abstract || '';
          const score = rec.score || 0;
          const reason = rec.reason || 'Recommended for you';
          
          return (
            <Grid item xs={12} md={6} lg={4} key={paperId || index}>
              <Card elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  {/* Score indicator */}
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Chip 
                      label={`Score: ${(score * 100).toFixed(1)}%`}
                      color={score > 0.7 ? "success" : score > 0.4 ? "warning" : "default"}
                      size="small"
                    />
                    <Typography variant="caption" color="text.secondary">
                      {reason}
                    </Typography>
                  </Box>

                  {/* Paper title */}
                  <Typography 
                    variant="h6" 
                    component="h2" 
                    gutterBottom
                    sx={{ 
                      fontWeight: 'bold',
                      color: 'primary.main',
                      '&:hover': { textDecoration: 'underline' }
                    }}
                  >
                    <Link to={`/papers/${paperId}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      {title}
                    </Link>
                  </Typography>

                  {/* Authors */}
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    By: {authors}
                  </Typography>

                  <Divider sx={{ my: 1 }} />

                  {/* Abstract preview */}
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      mb: 2,
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}
                  >
                    {abstract || 'No abstract available'}
                  </Typography>

                  {/* Actions */}
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Link to={`/papers/${paperId}`}>
                      <button startIcon={<VisibilityIcon />} size="small">
                        View Details
                      </button>
                    </Link>
                    
                    {/* Similarity score visualization */}
                    <Box display="flex" alignItems="center">
                      <Box 
                        sx={{ 
                          width: '60px',
                          height: '8px',
                          bgcolor: 'grey.300',
                          borderRadius: '4px',
                          overflow: 'hidden',
                          mr: 1
                        }}
                      >
                        <Box 
                          sx={{ 
                            width: `${score * 100}%`,
                            height: '100%',
                            bgcolor: score > 0.7 ? 'success.main' : score > 0.4 ? 'warning.main' : 'grey.500'
                          }}
                        />
                      </Box>
                      <Typography variant="caption">
                        {(score * 100).toFixed(0)}% match
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      <Box mt={3} textAlign="center">
        <Typography variant="body2" color="text.secondary">
          Showing {recommendations.length} recommendations based on your ratings and preferences.
        </Typography>
      </Box>
    </div>
  );
}

export default Recommendations;