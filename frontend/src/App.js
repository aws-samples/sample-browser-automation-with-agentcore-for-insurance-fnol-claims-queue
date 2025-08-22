import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [claims, setClaims] = useState([]);
  const [showDetailedView, setShowDetailedView] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(null);
  const [analyzedClaims, setAnalyzedClaims] = useState(new Set());
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [showClaimDialog, setShowClaimDialog] = useState(false);

  useEffect(() => {
    fetchClaims();
  }, []);

  const fetchClaims = async () => {
    try {
      const response = await axios.get('/api/claims');
      setClaims(response.data.claims);
    } catch (error) {
      console.error('Error fetching claims:', error);
    }
  };

  const openClaimDialog = (claim) => {
    setSelectedClaim(claim);
    setShowClaimDialog(true);
  };

  const closeClaimDialog = () => {
    setSelectedClaim(null);
    setShowClaimDialog(false);
    setAnalyzing(null);
  };

  const summarizeClaim = async (claimId) => {
    setAnalyzing(claimId);
    try {
      const response = await axios.post('/api/analyze-claim', {
        claim_id: claimId
      });
      
      // Update the selected claim with analysis results
      setSelectedClaim(prev => ({
        ...prev,
        complexity: response.data.complexity,
        new_status: response.data.new_status,
        reasoning: response.data.reasoning,
        analyzed: true
      }));
      
      // Mark this claim as analyzed
      setAnalyzedClaims(prev => new Set([...prev, claimId]));
      
      // Refresh claims list
      fetchClaims();
      
      setAnalyzing(null);
      
    } catch (error) {
      console.error('Error analyzing claim:', error);
      alert('Error analyzing claim. Please try again.');
      setAnalyzing(null);
    }
  };

  const ClaimCard = ({ claim, isDetailed = false }) => {
    const isAnalyzed = analyzedClaims.has(claim.id);
    const isCurrentlyAnalyzing = analyzing === claim.id;
    
    return (
      <div className={`claim-card ${isDetailed ? 'detailed' : ''}`}>
        <div className="claim-header">
          <h3>{claim.id}</h3>
          <span className={`status ${claim.status.toLowerCase().replace(' ', '-')}`}>
            {claim.status}
          </span>
        </div>
        
        <div className="claim-info">
          <p><strong>Type:</strong> {claim.type} - {claim.subtype}</p>
          <p><strong>Date of Loss:</strong> {claim.date_of_loss}</p>
          <p><strong>Description:</strong> {claim.description}</p>
          
          {isDetailed && (
            <>
              <p><strong>Policy Holder:</strong> {claim.policy_holder}</p>
              <p><strong>Policy Number:</strong> {claim.policy_number}</p>
              <p><strong>Estimated Damage:</strong> ${claim.estimated_damage.toLocaleString()}</p>
              
              <div className="evidence-section">
                <h4>Evidence Submitted:</h4>
                <ul>
                  <li>Images: {claim.evidence.images}</li>
                  <li>Videos: {claim.evidence.videos}</li>
                  <li>Voice Recordings: {claim.evidence.voice_recordings}</li>
                </ul>
              </div>
              
              <button 
                className={`analyze-btn ${isAnalyzed ? 'analyzed' : ''}`}
                onClick={() => openClaimDialog(claim)}
                disabled={isCurrentlyAnalyzing || isAnalyzed}
                title={isAnalyzed ? 'This claim has already been analyzed' : 'Open detailed analysis dialog'}
              >
                {isCurrentlyAnalyzing ? 'Analyzing...' : 
                 isAnalyzed ? 'Already Analyzed' : 'Analyze Complexity'}
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  const ClaimAnalysisDialog = () => {
    if (!showClaimDialog || !selectedClaim) return null;

    return (
      <div className="modal-overlay" onClick={closeClaimDialog}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>Claim Analysis - {selectedClaim.id}</h2>
            <button className="close-btn" onClick={closeClaimDialog}>×</button>
          </div>
          
          <div className="modal-content">
            <div className="claim-details-section">
              <h3>Claim Details</h3>
              <div className="details-grid">
                <div className="detail-item">
                  <label>Policy Holder:</label>
                  <span>{selectedClaim.policy_holder}</span>
                </div>
                <div className="detail-item">
                  <label>Policy Number:</label>
                  <span>{selectedClaim.policy_number}</span>
                </div>
                <div className="detail-item">
                  <label>Type:</label>
                  <span>{selectedClaim.type} - {selectedClaim.subtype}</span>
                </div>
                <div className="detail-item">
                  <label>Date of Loss:</label>
                  <span>{selectedClaim.date_of_loss}</span>
                </div>
                <div className="detail-item">
                  <label>Estimated Damage:</label>
                  <span>${selectedClaim.estimated_damage?.toLocaleString()}</span>
                </div>
                <div className="detail-item">
                  <label>Status:</label>
                  <span className={`status ${selectedClaim.status?.toLowerCase().replace(' ', '-')}`}>
                    {selectedClaim.status}
                  </span>
                </div>
              </div>
              
              <div className="description-section">
                <label>Description:</label>
                <p>{selectedClaim.description}</p>
              </div>
              
              <div className="evidence-details">
                <h4>Evidence Submitted:</h4>
                <div className="evidence-grid">
                  <div className="evidence-item">
                    <label>Images:</label>
                    <span>{selectedClaim.evidence?.images || 0}</span>
                  </div>
                  <div className="evidence-item">
                    <label>Videos:</label>
                    <span>{selectedClaim.evidence?.videos || 0}</span>
                  </div>
                  <div className="evidence-item">
                    <label>Voice Recordings:</label>
                    <span>{selectedClaim.evidence?.voice_recordings || 0}</span>
                  </div>
                </div>
              </div>
            </div>
            
            {selectedClaim.analyzed && (
              <div className="analysis-results">
                <h3>Analysis Results</h3>
                <div className="result-item">
                  <label>Complexity:</label>
                  <span className={`complexity ${selectedClaim.complexity?.toLowerCase()}`}>
                    {selectedClaim.complexity}
                  </span>
                </div>
                <div className="result-item">
                  <label>New Status:</label>
                  <span>{selectedClaim.new_status}</span>
                </div>
                <div className="result-item">
                  <label>Reasoning:</label>
                  <p>{selectedClaim.reasoning}</p>
                </div>
              </div>
            )}
          </div>
          
          <div className="modal-footer">
            {!selectedClaim.analyzed && (
              <button 
                className="summarize-btn"
                onClick={() => summarizeClaim(selectedClaim.id)}
                disabled={analyzing === selectedClaim.id}
              >
                {analyzing === selectedClaim.id ? 'Summarizing...' : 'Summarize'}
              </button>
            )}
            <button className="cancel-btn" onClick={closeClaimDialog}>
              {selectedClaim.analyzed ? 'Close' : 'Cancel'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>First Notice Of Loss - Claims Queue</h1>
        <div className="header-controls">
          <button 
            className="view-toggle-btn"
            onClick={() => setShowDetailedView(!showDetailedView)}
          >
            {showDetailedView ? 'Queue View' : 'Detailed View'}
          </button>
          <button className="refresh-btn" onClick={fetchClaims}>
            Refresh
          </button>
        </div>
      </header>

      <main className="main-content">
        {loading ? (
          <div className="loading">Loading claims...</div>
        ) : (
          <>
            <div className="claims-summary">
              <p>Total Active Claims: {claims.length}</p>
              <p>New Claims: {claims.filter(c => c.status === 'New').length}</p>
              <p>Needs Review: {claims.filter(c => c.status === 'Needs Review').length}</p>
            </div>

            <div className={`claims-container ${showDetailedView ? 'detailed-view' : 'queue-view'}`}>
              {claims.length === 0 ? (
                <div className="no-claims">No active claims to display</div>
              ) : (
                claims.map(claim => (
                  <ClaimCard 
                    key={claim.id} 
                    claim={claim} 
                    isDetailed={showDetailedView}
                  />
                ))
              )}
            </div>
          </>
        )}
      </main>

      {/* Modal Dialog */}
      <ClaimAnalysisDialog />
    </div>
  );
}

export default App;
