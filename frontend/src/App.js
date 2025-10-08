// File: frontend/src/App.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import AppShell from './layout/AppShell';
import IncompleteTickets from './tickets/IncompleteTickets';
import ResolutionDashboard from './tickets/ResolutionDashboard';
import SolutionModal from './tickets/SolutionModal';
import KnowledgeUpload from './knowledge/KnowledgeUpload';
import StatusAlert from './components/StatusAlert';
import { ThemeProvider } from '@mui/material/styles';
import theme from './theme';
import { Box } from '@mui/material';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  // State for Resolution Dashboard
  const [completeTickets, setCompleteTickets] = useState([]);
  const [loadingComplete, setLoadingComplete] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [solutions, setSolutions] = useState([]); // Current solutions for the selected ticket
  
  // Initialize cached solutions from localStorage if available
  const [cachedSolutions, setCachedSolutions] = useState(() => {
    const saved = localStorage.getItem('cachedSolutions');
    return saved ? JSON.parse(saved) : {};
  });
  
  const [generatingSolutions, setGeneratingSolutions] = useState(false);
  const [showSolutionModal, setShowSolutionModal] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);
  const [submittingResolution, setSubmittingResolution] = useState(false);
  
  // State for Incomplete Tickets Tab
  const [incompleteTickets, setIncompleteTickets] = useState([]);
  const [loadingIncomplete, setLoadingIncomplete] = useState(false);
  const [nextPollEta, setNextPollEta] = useState(null); // timestamp of next expected poll
  const [countdown, setCountdown] = useState('');

  // State for Knowledge Management
  const [knowledgeFile, setKnowledgeFile] = useState(null);
  const [ragFile, setRagFile] = useState(null);
  const [uploadingKnowledge, setUploadingKnowledge] = useState(false);
  const [uploadingRag, setUploadingRag] = useState(false);
  
  // General messaging state
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [uploadStatus, setUploadStatus] = useState({ success: false, message: '', error: '' });

  // Fetch data on component mount and when active tab changes
  useEffect(() => {
    if (activeTab === 'dashboard') {
      fetchCompleteTickets();
    } else if (activeTab === 'incomplete') {
      fetchIncompleteTickets();
    }
  }, [activeTab]);
  
  // Save cached solutions to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('cachedSolutions', JSON.stringify(cachedSolutions));
  }, [cachedSolutions]);

  // Countdown for next poll based on backend's adaptive polling interval
  useEffect(() => {
    const ticker = setInterval(() => {
      if (nextPollEta) {
        const delta = nextPollEta - Date.now();
        if (delta <= 0) {
          setCountdown('Polling...');
          // refresh incomplete tickets automatically at poll boundary
          fetchIncompleteTickets();
          // The new poll time will be set by the response from fetchIncompleteTickets
        } else {
          const m = Math.floor(delta / 60000);
          const s = Math.floor((delta % 60000) / 1000);
          setCountdown(`${m}:${s.toString().padStart(2,'0')}`);
        }
      }
    }, 1000);
    return () => clearInterval(ticker);
  }, [nextPollEta]);

  const fetchCompleteTickets = async () => {
    setLoadingComplete(true);
    setError(null);
    try {
      const response = await axios.get('/api/complete-tickets');
      setCompleteTickets(response.data.tickets);
    } catch (err) {
      setError('Failed to fetch complete tickets.');
    } finally {
      setLoadingComplete(false);
    }
  };
  
  const fetchIncompleteTickets = async () => {
    setLoadingIncomplete(true);
    setError(null);
    try {
      const response = await axios.get('/api/incomplete-tickets');
      setIncompleteTickets(response.data.tickets);
      
      // Update the next poll time from the backend
      if (response.data.next_poll_time) {
        setNextPollEta(response.data.next_poll_time);
      }
    } catch (err) {
      setError('Failed to fetch incomplete tickets.');
    } finally {
      setLoadingIncomplete(false);
    }
  };
  
  // Function to select a ticket and show its cached solutions if they exist
  const handleSelectTicket = (ticketKey) => {
    setSelectedTicket(ticketKey);
    if (ticketKey && cachedSolutions[ticketKey]) {
      setSolutions(cachedSolutions[ticketKey]);
    } else {
      setSolutions([]);
    }
  };

  const handleGenerateSolutions = async (ticketKey) => {
    setSelectedTicket(ticketKey);
    
    // If we're selecting a new ticket that has cached solutions, use those
    if (ticketKey && cachedSolutions[ticketKey]) {
      setSolutions(cachedSolutions[ticketKey]);
      return;
    }
    
    // If we need to generate new solutions
    setGeneratingSolutions(true);
    setSolutions([]);
    
    if (ticketKey) {
      try {
        const response = await axios.post(`/api/generate-solutions/${ticketKey}`);
        const newSolutions = response.data.solutions;
        
        // Update the current solutions
        setSolutions(newSolutions);
        
        // Cache the solutions for this ticket
        setCachedSolutions(prev => ({
          ...prev,
          [ticketKey]: newSolutions
        }));
      } catch (err) {
        setError(`Failed to generate solutions for ticket ${ticketKey}.`);
      } finally {
        setGeneratingSolutions(false);
      }
    }
  };

  const handleReviewSolution = (solution) => {
    setSelectedSolution(JSON.parse(JSON.stringify(solution))); // Deep copy to allow editing
    setShowSolutionModal(true);
  };
  
  const handleSubmitResolution = async () => {
    if (!selectedTicket || !selectedSolution) return;
    setSubmittingResolution(true);
    try {
      await axios.post(`/api/post-solution/${selectedTicket}`, {
        solution_text: selectedSolution.solution_text,
        llm_provider_model: selectedSolution.llm_provider_model
      });
      setSuccessMessage(`Solution successfully posted to JIRA ticket ${selectedTicket}`);
      setShowSolutionModal(false);
      setCompleteTickets(completeTickets.filter(ticket => ticket.ticket_key !== selectedTicket));
      
      // Also remove from cached solutions since ticket is now resolved
      setCachedSolutions(prev => {
        const newCache = {...prev};
        delete newCache[selectedTicket];
        return newCache;
      });
      
      setSelectedTicket(null);
      setSolutions([]);
    } catch (err) {
      setError(`Failed to post solution to ticket ${selectedTicket}.`);
    } finally {
      setSubmittingResolution(false);
    }
  };

  const handleFileUpload = async (fileType) => {
    let file, endpoint, setUploading;
    if (fileType === 'knowledge') {
      file = knowledgeFile;
      endpoint = '/api/upload-knowledge';
      setUploading = setUploadingKnowledge;
    } else {
      file = ragFile;
      endpoint = '/api/upload-solved-tickets';
      setUploading = setUploadingRag;
    }

    if (!file) {
      setUploadStatus({ success: false, message: '', error: 'Please select a file to upload.' });
      return;
    }

    setUploading(true);
    setUploadStatus({ success: false, message: '', error: '' });
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setUploadStatus({ success: true, message: response.data.message, error: '' });
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setUploadStatus({ success: false, message: '', error: `Upload failed: ${errorMessage}` });
    } finally {
      setUploading(false);
    }
  };

  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'N/A';
    const date = new Date(dateTimeStr);
    return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  };

  return (
    <ThemeProvider theme={theme}>
      {/* Snackbar style alerts */}
      <StatusAlert open={!!successMessage} severity="success" message={successMessage} onClose={() => setSuccessMessage(null)} />
      <StatusAlert open={!!error} severity="error" message={error} onClose={() => setError(null)} />
      <StatusAlert open={!!uploadStatus.message} severity="success" message={uploadStatus.message} onClose={() => setUploadStatus({ ...uploadStatus, message: '' })} />
      <StatusAlert open={!!uploadStatus.error} severity="error" message={uploadStatus.error} onClose={() => setUploadStatus({ ...uploadStatus, error: '' })} />
      <AppShell value={activeTab} onChange={setActiveTab}>
        {activeTab === 'incomplete' && (
          <IncompleteTickets
            loading={loadingIncomplete}
            tickets={incompleteTickets}
            countdown={countdown}
            formatDateTime={formatDateTime}
          />
        )}
        {activeTab === 'dashboard' && (
          <ResolutionDashboard
            tickets={completeTickets}
            loadingTickets={loadingComplete}
            selectedTicket={selectedTicket}
            onSelectTicket={handleSelectTicket}
            onGenerate={(ticketKey) => {
              if (ticketKey === null) return fetchCompleteTickets();
              handleGenerateSolutions(ticketKey);
            }}
            generatingSolutions={generatingSolutions}
            solutions={solutions}
            formatDateTime={formatDateTime}
            hasCachedSolutions={(ticketKey) => Boolean(cachedSolutions[ticketKey])}
            onReviewSolution={handleReviewSolution}
          />
        )}
        {activeTab === 'admin' && (
          <KnowledgeUpload
            onUploadKnowledge={() => handleFileUpload('knowledge')}
            onUploadRag={() => handleFileUpload('rag')}
            knowledgeFile={knowledgeFile}
            setKnowledgeFile={setKnowledgeFile}
            ragFile={ragFile}
            setRagFile={setRagFile}
            uploadingKnowledge={uploadingKnowledge}
            uploadingRag={uploadingRag}
          />
        )}
      </AppShell>
      <SolutionModal
        open={showSolutionModal}
        onClose={() => setShowSolutionModal(false)}
        ticketKey={selectedTicket}
        solution={selectedSolution}
        onChange={setSelectedSolution}
        onSubmit={handleSubmitResolution}
        submitting={submittingResolution}
      />
    </ThemeProvider>
  );
}

export default App;
