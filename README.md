# Paper Recommendation Platform

A comprehensive platform for users to upload, discover, and get recommendations for academic papers using a hybrid recommender system (collaborative + content-based filtering).

## Features

- **User Management**: Registration, authentication, and profile management
- **Field Management**: Users can add their research fields/interests
- **Paper Upload**: Upload papers with metadata (title, authors, abstract, tags, PDF files)
- **Paper Browsing**: Search and filter papers by title, authors, abstract, or tags
- **Rating System**: Rate papers on a 1-5 scale
- **Hybrid Recommender System**: 
  - Content-based filtering using TF-IDF and cosine similarity
  - Collaborative filtering using SVD matrix factorization
  - Weighted combination of both approaches
- **Similar Papers**: Find papers similar to a given paper using content-based features
- **Tagging System**: Tag papers for better organization and discovery
- **Admin Dashboard**: Metrics and statistics for platform administrators

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database management
- **SQLite**: Database (can be upgraded to PostgreSQL)
- **scikit-learn**: Machine learning for recommendations
- **pandas/numpy**: Data processing

### Frontend
- **React**: UI framework
- **React Router**: Routing
- **Axios**: HTTP client
- **Recharts**: Data visualization for admin dashboard
- **Vite**: Build tool

## Setup Instructions

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the backend server:
```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /register` - Register a new user
- `POST /token` - Login and get access token
- `GET /users/me` - Get current user info

### User Fields
- `POST /users/fields` - Add a research field
- `GET /users/fields` - Get user's fields

### Papers
- `POST /papers` - Upload a new paper
- `GET /papers` - List papers (with search and tag filters)
- `GET /papers/{id}` - Get paper details
- `GET /papers/{id}/similar` - Get similar papers

### Ratings
- `POST /papers/{id}/ratings` - Rate a paper

### Recommendations
- `GET /recommendations` - Get personalized recommendations

### Tags
- `GET /tags` - List all tags

### Admin
- `GET /admin/metrics` - Get platform metrics (admin only)

## Usage

1. **Register/Login**: Create an account or login
2. **Add Fields**: Add your research fields on the dashboard
3. **Upload Papers**: Upload papers you like with tags
4. **Rate Papers**: Rate papers to improve recommendations
5. **Get Recommendations**: View personalized paper recommendations
6. **Find Similar Papers**: Click "Find Similar Papers" on any paper
7. **Search**: Use the search bar to find papers by keywords
8. **Filter by Tags**: Filter papers by tags using the dropdown

## Admin Features

Admins can access the admin dashboard to view:
- Total users, papers, ratings, and tags
- Average rating across all papers
- Papers per user ratio
- Top tags visualization (bar chart and pie chart)

## Recommendation Algorithm

The hybrid recommender combines:

1. **Content-Based Filtering (60% weight)**:
   - Uses TF-IDF vectorization on paper title, abstract, authors, and tags
   - Calculates cosine similarity between papers
   - Recommends papers similar to ones the user rated highly

2. **Collaborative Filtering (40% weight)**:
   - Uses SVD (Singular Value Decomposition) for dimensionality reduction
   - Finds users with similar rating patterns
   - Recommends papers liked by similar users

The final recommendation score is a weighted combination of both approaches.

## Project Structure

```
.
├── backend/
│   ├── main.py          # FastAPI application
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── recommender.py   # Hybrid recommender system
│   └── search.py        # Search functionality
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── App.jsx      # Main app component
│   │   └── main.jsx     # Entry point
│   └── package.json
├── requirements.txt     # Python dependencies
└── README.md
```

## Future Enhancements

- PDF text extraction for better content analysis
- Advanced search with full-text search capabilities
- Paper collections/reading lists
- Social features (comments, sharing)
- Export recommendations
- Email notifications for new recommendations
- Integration with external paper databases (arXiv, PubMed, etc.)

## License

MIT License




