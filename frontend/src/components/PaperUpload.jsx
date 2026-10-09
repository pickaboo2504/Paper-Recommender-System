import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './PaperUpload.css'

function PaperUpload({ user }) {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    title: '',
    authors: '',
    abstract: '',
    tags: '',
    doi: ''
  })
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fetchingMeta, setFetchingMeta] = useState(false)

  const fetchMetadata = async () => {
    if (!formData.doi.trim()) {
      setError('Please enter a DOI or URL first')
      return
    }
    setError('')
    setFetchingMeta(true)
    try {
      const response = await axios.get('/metadata', {
        params: { identifier: formData.doi.trim() },
      })
      const meta = response.data || {}
      setFormData((prev) => ({
        ...prev,
        title: meta.title || prev.title,
        authors: meta.authors || prev.authors,
        abstract: meta.abstract || prev.abstract,
        doi: meta.doi || prev.doi,
      }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch metadata')
    } finally {
      setFetchingMeta(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const formDataObj = new FormData()
      formDataObj.append('title', formData.title)
      formDataObj.append('authors', formData.authors)
      formDataObj.append('abstract', formData.abstract)
      formDataObj.append('tags', formData.tags)
      if (formData.doi) {
        formDataObj.append('doi', formData.doi)
      }
      if (file) {
        formDataObj.append('file', file)
      }

      await axios.post('/papers', formDataObj, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      navigate('/papers')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload paper')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>Upload Paper</h1>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="input"
            required
          />
          <input
            type="text"
            placeholder="Authors (comma-separated)"
            value={formData.authors}
            onChange={(e) => setFormData({ ...formData, authors: e.target.value })}
            className="input"
            required
          />
          <textarea
            placeholder="Abstract"
            value={formData.abstract}
            onChange={(e) => setFormData({ ...formData, abstract: e.target.value })}
            className="textarea"
            required
          />
          <input
            type="text"
            placeholder="Tags (comma-separated, e.g., machine learning, AI, deep learning)"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
            className="input"
          />
          <input
            type="text"
            placeholder="DOI or full URL to the paper (optional)"
            value={formData.doi}
            onChange={(e) => setFormData({ ...formData, doi: e.target.value })}
            className="input"
          />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchMetadata}
            disabled={fetchingMeta}
            style={{ marginBottom: '16px' }}
          >
            {fetchingMeta ? 'Fetching metadata...' : 'Fetch from DOI/URL'}
          </button>
          <div className="file-upload">
            <label htmlFor="file">Upload PDF (optional):</label>
            <input
              type="file"
              id="file"
              accept=".pdf"
              onChange={(e) => setFile(e.target.files[0])}
              className="input"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Uploading...' : 'Upload Paper'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default PaperUpload




