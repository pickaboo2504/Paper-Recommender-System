import React, { useState, useEffect } from 'react'
import axios from 'axios'
import PaperCard from './PaperCard'
import './PaperList.css'

function PaperList({ user }) {
  const [papers, setPapers] = useState([])
  const [tags, setTags] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTag, setSelectedTag] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPapers()
    fetchTags()
  }, [searchTerm, selectedTag])

  const fetchPapers = async () => {
    setLoading(true)
    try {
      let url = '/papers?limit=100'
      if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`
      if (selectedTag) url += `&tag=${encodeURIComponent(selectedTag)}`
      
      const response = await axios.get(url)
      setPapers(response.data)
    } catch (error) {
      console.error('Error fetching papers:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTags = async () => {
    try {
      const response = await axios.get('/tags')
      setTags(response.data)
    } catch (error) {
      console.error('Error fetching tags:', error)
    }
  }

  return (
    <div className="container">
      <div className="paper-list-header">
        <h1>Browse Papers</h1>
        <div className="search-filters">
          <input
            type="text"
            placeholder="Search papers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input search-input"
          />
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="input tag-filter"
          >
            <option value="">All Tags</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.name}>
                {tag.name} ({tag.count})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading papers...</div>
      ) : (
        <div className="papers-grid">
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} user={user} onUpdate={fetchPapers} />
          ))}
          {papers.length === 0 && (
            <div className="empty-state">No papers found</div>
          )}
        </div>
        
      )}
    </div>
  )
}

export default PaperList




