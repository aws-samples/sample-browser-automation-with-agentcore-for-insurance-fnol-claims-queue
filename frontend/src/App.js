import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  const [evidenceAnalysis, setEvidenceAnalysis] = useState({});
  const [activeEvidenceTabs, setActiveEvidenceTabs] = useState({});
  
  // New state for evidence modals
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceModalData, setEvidenceModalData] = useState(null);
  const loadedEvidenceRef = useRef({});
  const [forceUpdate, setForceUpdate] = useState(0);

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

  const getPresignedUrl = async (s3Url) => {
    try {
      const response = await axios.get(`/api/presigned-url?s3_url=${encodeURIComponent(s3Url)}`);
      return response.data.presigned_url;
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      return null;
    }
  };

  const getActiveEvidenceTab = (claimId) => {
    return activeEvidenceTabs[claimId] || null;
  };

  const loadEvidenceUrls = useCallback((claimId, evidenceType) => {
    const claim = claims.find(c => c.claim_id === claimId);
    if (claim && claim.evidence_urls && claim.evidence_urls[evidenceType]) {
      loadedEvidenceRef.current[`${claimId}_${evidenceType}`] = claim.evidence_urls[evidenceType];
      setForceUpdate(prev => prev + 1);
    }
  }, [claims]);

  const setActiveEvidenceTab = useCallback((claimId, tab) => {
    setActiveEvidenceTabs(prev => ({
      ...prev,
      [claimId]: prev[claimId] === tab ? null : tab
    }));
    
    // Load evidence URLs when tab is activated
    if (tab) {
      loadEvidenceUrls(claimId, tab);
    }
  }, [loadEvidenceUrls]);

  const analyzeEvidence = useCallback(async (claimId, evidenceType, fromModal = false) => {
    try {
      console.log(`Starting analysis for ${claimId} - ${evidenceType}`);
      
      // Set loading state
      setAnalyzing(`${claimId}_${evidenceType}`);
      
      // Load evidence URLs immediately when starting analysis (only if NOT from modal)
      if (!fromModal) {
        loadEvidenceUrls(claimId, evidenceType);
      }
      
      const response = await axios.post(`/api/claims/${claimId}/analyze-${evidenceType}`);
      console.log(`Analysis response for ${claimId} - ${evidenceType}:`, response.data);
      
      if (response.data.status === 'processing') {
        // Start polling for results
        pollForAnalysisResults(claimId, evidenceType, fromModal);
      }
      
    } catch (error) {
      console.error(`Error starting ${evidenceType} analysis for ${claimId}:`, error);
      setAnalyzing(null);
      
      if (error.response) {
        alert(`Error starting ${evidenceType} analysis: ${error.response.data.detail || error.response.statusText}`);
      } else if (error.request) {
        alert(`Network error: Cannot reach server. Please check if the application is running.`);
      } else {
        alert(`Error starting ${evidenceType} analysis: ${error.message}`);
      }
    }
  }, [loadEvidenceUrls]);

  const pollForAnalysisResults = useCallback((claimId, evidenceType, fromModal = false) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/claims/${claimId}`);
        const claim = response.data;
        const analysisStatus = claim.evidence_analysis?.[evidenceType]?.status;
        
        if (analysisStatus === 'completed') {
          // Analysis complete - update claims and stop polling
          setClaims(prevClaims => 
            prevClaims.map(c => 
              c.claim_id === claimId 
                ? { ...c, evidence_analysis: claim.evidence_analysis }
                : c
            )
          );
          setAnalyzing(null);
          clearInterval(pollInterval);
          
          // Load evidence URLs only if NOT from modal (to avoid updating main page)
          if (!fromModal && claim.evidence_urls?.[evidenceType]) {
            loadedEvidenceRef.current[`${claimId}_${evidenceType}`] = claim.evidence_urls[evidenceType];
            setForceUpdate(prev => prev + 1);
            // Set active tab to show the analyzed evidence
            setActiveEvidenceTab(claimId, evidenceType);
          } else if (fromModal && claim.evidence_urls?.[evidenceType]) {
            // For modal, still load URLs but don't set active tab
            loadedEvidenceRef.current[`${claimId}_${evidenceType}`] = claim.evidence_urls[evidenceType];
            setForceUpdate(prev => prev + 1);
          }
          
        } else if (analysisStatus === 'error') {
          // Analysis failed - stop polling and show error
          setAnalyzing(null);
          clearInterval(pollInterval);
          alert(`${evidenceType} analysis failed. Please try again.`);
          
        } else if (analysisStatus !== 'processing') {
          // Unexpected status - stop polling
          setAnalyzing(null);
          clearInterval(pollInterval);
        }
        
      } catch (error) {
        console.error(`Error polling for ${evidenceType} analysis results:`, error);
        setAnalyzing(null);
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds
    
    // Cleanup after 10 minutes to prevent infinite polling
    setTimeout(() => {
      clearInterval(pollInterval);
      if (analyzing === `${claimId}_${evidenceType}`) {
        setAnalyzing(null);
        alert(`${evidenceType} analysis timed out. Please try again.`);
      }
    }, 600000); // 10 minutes
  }, [analyzing]);

  const summarizeClaim = useCallback(async (claimId) => {
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
  }, [analyzing, analyzedClaims]);

  // Evidence Modal Functions
  const openEvidenceModal = (claimId, evidenceType, claim) => {
    setEvidenceModalData({
      claimId,
      evidenceType,
      claim,
      evidenceItems: getEvidenceItems(claim, evidenceType)
    });
    setShowEvidenceModal(true);
  };

  const closeEvidenceModal = () => {
    setShowEvidenceModal(false);
    setEvidenceModalData(null);
  };

  const getEvidenceItems = (claim, evidenceType) => {
    switch (evidenceType) {
      case 'images':
        return Array.from({ length: claim.evidence.images }, (_, i) => ({
          type: 'image',
          name: `Image ${i + 1}`,
          id: i
        }));
      case 'videos':
        return Array.from({ length: claim.evidence.videos }, (_, i) => ({
          type: 'video',
          name: `Video ${i + 1}`,
          id: i
        }));
      case 'audio':
        return Array.from({ length: claim.evidence.voice_recordings }, (_, i) => ({
          type: 'audio',
          name: `Audio Recording ${i + 1}`,
          id: i
        }));
      default:
        return [];
    }
  };

  const startEvidenceAnalysis = async () => {
    if (!evidenceModalData) return;
    
    const { claimId, evidenceType } = evidenceModalData;
    // Don't close modal - keep it open to show content
    // Pass fromModal=true to prevent main page updates
    await analyzeEvidence(claimId, evidenceType, true);
  };

  const EvidenceImage = ({ s3Url, alt }) => {
    const [presignedUrl, setPresignedUrl] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const fetchUrl = async () => {
        const url = await getPresignedUrl(s3Url);
        setPresignedUrl(url);
        setLoading(false);
      };
      fetchUrl();
    }, [s3Url]);

    if (loading) return <div className="evidence-loading">Loading...</div>;
    if (!presignedUrl) return <div className="evidence-error">Failed to load image</div>;

    return <img src={presignedUrl} alt={alt} className="evidence-image" />;
  };

  const EvidenceVideo = React.memo(({ s3Url }) => {
    const [presignedUrl, setPresignedUrl] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const fetchUrl = async () => {
        const url = await getPresignedUrl(s3Url);
        setPresignedUrl(url);
        setLoading(false);
      };
      fetchUrl();
    }, [s3Url]);

    if (loading) return <div className="evidence-loading">Loading...</div>;
    if (!presignedUrl) return <div className="evidence-error">Failed to load video</div>;

    return <video src={presignedUrl} controls className="evidence-video" />;
  });

  const EvidenceAudio = ({ s3Url }) => {
    const [presignedUrl, setPresignedUrl] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const fetchUrl = async () => {
        const url = await getPresignedUrl(s3Url);
        setPresignedUrl(url);
        setLoading(false);
      };
      fetchUrl();
    }, [s3Url]);

    if (loading) return <div className="evidence-loading">Loading...</div>;
    if (!presignedUrl) return <div className="evidence-error">Failed to load audio</div>;

    return <audio src={presignedUrl} controls className="evidence-audio" />;
  };

  const ClaimCard = React.memo(({ claim, isDetailed = false }) => {
    const isAnalyzed = analyzedClaims.has(claim.claim_id);
    const isCurrentlyAnalyzing = analyzing === claim.claim_id;
    
    return (
      <div className={`claim-card ${isDetailed ? 'detailed' : ''}`}>
        <div className="claim-header">
          <h3>{claim.claim_id}</h3>
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
                
                <div className="evidence-tabs">
                  <div className={`evidence-tab ${getActiveEvidenceTab(claim.claim_id) === 'images' ? 'active' : ''} ${claim.evidence_analysis?.images?.status === 'completed' ? 'analyzed' : ''}`}>
                    <div className="tab-header">
                      <span 
                        className={`tab-title ${claim.evidence_analysis?.images?.status === 'completed' ? 'clickable' : ''}`}
                        onClick={() => claim.evidence_analysis?.images?.status === 'completed' && setActiveEvidenceTab(claim.claim_id, 'images')}
                      >
                        Images ({claim.evidence.images})
                        {claim.evidence_analysis?.images?.status === 'completed' && <span className="checkmark">✅</span>}
                      </span>
                      <button 
                        className="analyze-btn small"
                        onClick={() => openEvidenceModal(claim.claim_id, 'images', claim)}
                        disabled={claim.evidence_analysis?.images?.status === 'completed' || 
                                 claim.evidence_analysis?.images?.status === 'processing' || 
                                 analyzing === `${claim.claim_id}_images`}
                      >
                        {analyzing === `${claim.claim_id}_images` ? 'Processing...' : 
                         claim.evidence_analysis?.images?.status === 'processing' ? 'Processing...' : 'Analyze Images'}
                      </button>
                    </div>
                    <div className="evidence-tags-box">
                      {claim.evidence_analysis?.images?.status === 'completed' 
                        ? claim.evidence_analysis.images.tags?.join(', ') || 'No tags found'
                        : 'Analysis tags will appear here...'}
                    </div>
                    {getActiveEvidenceTab(claim.claim_id) === 'images' && loadedEvidenceRef.current[`${claim.claim_id}_images`] && (
                      <div className="evidence-content">
                        <div className="images-grid">
                          {loadedEvidenceRef.current[`${claim.claim_id}_images`].map((url, index) => (
                            <EvidenceImage key={`${claim.claim_id}-image-${index}`} s3Url={url} alt={`Evidence ${index + 1}`} />
                          ))}
                        </div>
                      </div>
                    )}
                    {getActiveEvidenceTab(claim.claim_id) === 'images' && !loadedEvidenceRef.current[`${claim.claim_id}_images`] && (
                      <div className="evidence-placeholder">
                        <p>Click "Analyze Images" to load and analyze images for this claim</p>
                      </div>
                    )}
                  </div>
                  
                  <div className={`evidence-tab ${getActiveEvidenceTab(claim.claim_id) === 'videos' ? 'active' : ''} ${claim.evidence_analysis?.videos?.status === 'completed' ? 'analyzed' : ''}`}>
                    <div className="tab-header">
                      <span 
                        className={`tab-title ${claim.evidence_analysis?.videos?.status === 'completed' ? 'clickable' : ''}`}
                        onClick={() => claim.evidence_analysis?.videos?.status === 'completed' && setActiveEvidenceTab(claim.claim_id, 'videos')}
                      >
                        Videos ({claim.evidence.videos})
                        {claim.evidence_analysis?.videos?.status === 'completed' && <span className="checkmark">✅</span>}
                      </span>
                      <button 
                        className="analyze-btn small"
                        onClick={() => openEvidenceModal(claim.claim_id, 'videos', claim)}
                        disabled={claim.evidence_analysis?.videos?.status === 'completed' || 
                                 claim.evidence_analysis?.videos?.status === 'processing' || 
                                 analyzing === `${claim.claim_id}_videos`}
                      >
                        {analyzing === `${claim.claim_id}_videos` ? 'Processing...' : 
                         claim.evidence_analysis?.videos?.status === 'processing' ? 'Processing...' : 'Analyze Videos'}
                      </button>
                    </div>
                    <div className="evidence-tags-box">
                      {claim.evidence_analysis?.videos?.status === 'completed' 
                        ? claim.evidence_analysis.videos.tags?.join(', ') || 'No tags found'
                        : 'Analysis tags will appear here...'}
                    </div>
                    {getActiveEvidenceTab(claim.claim_id) === 'videos' && loadedEvidenceRef.current[`${claim.claim_id}_videos`] && (
                      <div className="evidence-content">
                        <div className="videos-grid">
                          {loadedEvidenceRef.current[`${claim.claim_id}_videos`].map((url, index) => (
                            <EvidenceVideo key={`${claim.claim_id}-video-${index}`} s3Url={url} />
                          ))}
                        </div>
                      </div>
                    )}
                    {getActiveEvidenceTab(claim.claim_id) === 'videos' && !loadedEvidenceRef.current[`${claim.claim_id}_videos`] && (
                      <div className="evidence-placeholder">
                        <p>Click "Analyze Videos" to load and analyze videos for this claim</p>
                      </div>
                    )}
                  </div>
                  
                  <div className={`evidence-tab ${getActiveEvidenceTab(claim.claim_id) === 'audio' ? 'active' : ''} ${claim.evidence_analysis?.audio?.status === 'completed' ? 'analyzed' : ''}`}>
                    <div className="tab-header">
                      <span 
                        className={`tab-title ${claim.evidence_analysis?.audio?.status === 'completed' ? 'clickable' : ''}`}
                        onClick={() => claim.evidence_analysis?.audio?.status === 'completed' && setActiveEvidenceTab(claim.claim_id, 'audio')}
                      >
                        Audio ({claim.evidence.voice_recordings})
                        {claim.evidence_analysis?.audio?.status === 'completed' && <span className="checkmark">✅</span>}
                      </span>
                      <button 
                        className="analyze-btn small"
                        onClick={() => openEvidenceModal(claim.claim_id, 'audio', claim)}
                        disabled={claim.evidence_analysis?.audio?.status === 'completed' || 
                                 claim.evidence_analysis?.audio?.status === 'processing' || 
                                 analyzing === `${claim.claim_id}_audio`}
                      >
                        {analyzing === `${claim.claim_id}_audio` ? 'Processing...' : 
                         claim.evidence_analysis?.audio?.status === 'processing' ? 'Processing...' : 'Analyze Audio'}
                      </button>
                    </div>
                    <div className="evidence-tags-box">
                      {claim.evidence_analysis?.audio?.status === 'completed' 
                        ? claim.evidence_analysis.audio.tags?.join(', ') || 'No tags found'
                        : 'Analysis tags will appear here...'}
                    </div>
                    {getActiveEvidenceTab(claim.claim_id) === 'audio' && loadedEvidenceRef.current[`${claim.claim_id}_audio`] && (
                      <div className="evidence-content">
                        <div className="audio-grid">
                          {loadedEvidenceRef.current[`${claim.claim_id}_audio`].map((url, index) => (
                            <EvidenceAudio key={`${claim.claim_id}-audio-${index}`} s3Url={url} />
                          ))}
                        </div>
                      </div>
                    )}
                    {getActiveEvidenceTab(claim.claim_id) === 'audio' && !loadedEvidenceRef.current[`${claim.claim_id}_audio`] && (
                      <div className="evidence-placeholder">
                        <p>Click "Analyze Audio" to load and analyze audio files for this claim</p>
                      </div>
                    )}
                  </div>
                </div>
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
  });

  const ClaimAnalysisDialog = () => {
    if (!showClaimDialog || !selectedClaim) return null;

    return (
      <div className="modal-overlay" onClick={closeClaimDialog}>
        <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>Claim Analysis - {selectedClaim.claim_id}</h2>
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
                onClick={() => summarizeClaim(selectedClaim.claim_id)}
                disabled={analyzing === selectedClaim.claim_id}
              >
                {analyzing === selectedClaim.claim_id ? 'Summarizing...' : 'Summarize'}
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

  // Evidence Modal Component
  const EvidenceModal = () => {
    if (!showEvidenceModal || !evidenceModalData) return null;

    const { claimId, evidenceType, claim, evidenceItems } = evidenceModalData;
    const isAnalyzing = analyzing === `${claimId}_${evidenceType}`;
    const isCompleted = claim.evidence_analysis?.[evidenceType]?.status === 'completed';
    const evidenceUrls = loadedEvidenceRef.current[`${claimId}_${evidenceType}`];

    return (
      <div className="modal-overlay">
        <div className="modal evidence-modal">
          <div className="modal-header">
            <h2>Analyze {evidenceType.charAt(0).toUpperCase() + evidenceType.slice(1)} - {claimId}</h2>
            <button className="close-btn" onClick={closeEvidenceModal}>×</button>
          </div>
          
          <div className="modal-body">
            {!evidenceUrls && !isAnalyzing && !isCompleted && (
              <div className="evidence-items-list">
                <h3>Items to Analyze ({evidenceItems.length})</h3>
                <div className="items-grid">
                  {evidenceItems.map((item, index) => (
                    <div key={index} className="evidence-item-card">
                      <div className="item-icon">
                        {item.type === 'image' && '🖼️'}
                        {item.type === 'video' && '🎥'}
                        {item.type === 'audio' && '🎵'}
                      </div>
                      <div className="item-name">{item.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {isAnalyzing && (
              <div className="analysis-status">
                <h3>Analyzing {evidenceType}...</h3>
                <p>Please wait while we process the {evidenceType}.</p>
              </div>
            )}

            {evidenceUrls && (
              <div className="evidence-content">
                <h3>{evidenceType.charAt(0).toUpperCase() + evidenceType.slice(1)} Content</h3>
                <div className="evidence-display">
                  {evidenceType === 'images' && evidenceUrls.map((url, index) => (
                    <EvidenceImage key={index} s3Url={url} alt={`Evidence ${index + 1}`} />
                  ))}
                  {evidenceType === 'videos' && evidenceUrls.map((url, index) => (
                    <EvidenceVideo key={index} s3Url={url} />
                  ))}
                  {evidenceType === 'audio' && evidenceUrls.map((url, index) => (
                    <EvidenceAudio key={index} s3Url={url} />
                  ))}
                </div>
              </div>
            )}
            
            {isCompleted && claim.evidence_analysis?.[evidenceType] && (
              <div className="analysis-results">
                <h4>Analysis Complete</h4>
                <div className="evidence-tags">
                  {claim.evidence_analysis[evidenceType].tags?.join(', ')}
                </div>
              </div>
            )}
          </div>
          
          <div className="modal-footer">
            {!isCompleted && !evidenceUrls && !isAnalyzing && (
              <button 
                className="start-analysis-btn"
                onClick={startEvidenceAnalysis}
                disabled={isAnalyzing}
              >
                Start Analyzing {evidenceType.charAt(0).toUpperCase() + evidenceType.slice(1)}
              </button>
            )}
            <button className="cancel-btn" onClick={closeEvidenceModal}>
              {isCompleted || evidenceUrls ? 'Close' : 'Cancel'}
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
                    key={claim.claim_id} 
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
      <EvidenceModal />
    </div>
  );
}

export default App;
