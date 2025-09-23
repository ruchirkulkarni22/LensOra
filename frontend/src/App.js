// File: frontend/src/App.js
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Badge, Button, Spinner, Alert, Modal, Form, Tab, Nav } from 'react-bootstrap';
import axios from 'axios';
import { FaCheckCircle, FaExclamationCircle, FaList, FaSearch, FaUserCog, FaUpload, FaBrain, FaBook, FaTasks, FaHistory } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  // State for tabs
  const [activeTab, setActiveTab] = useState('dashboard');

  // State for Resolution Dashboard
  const [completeTickets, setCompleteTickets] = useState([]);
  const [loadingComplete, setLoadingComplete] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [solutions, setSolutions] = useState([]);
  const [generatingSolutions, setGeneratingSolutions] = useState(false);
  const [showSolutionModal, setShowSolutionModal] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);
  const [submittingResolution, setSubmittingResolution] = useState(false);
  
  // State for Incomplete Tickets Tab
  const [incompleteTickets, setIncompleteTickets] = useState([]);
  const [loadingIncomplete, setLoadingIncomplete] = useState(false);
  const [pollingLogs, setPollingLogs] = useState([]);

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

  // Effect for Server-Sent Events (SSE) for polling logs
  useEffect(() => {
    const eventSource = new EventSource('/api/polling-logs');
    
    eventSource.onopen = () => {
      setPollingLogs(prev => ['[INFO] Live log stream connected.', ...prev].slice(0, 100));
    };

    eventSource.onmessage = (event) => {
      setPollingLogs(prev => [event.data, ...prev].slice(0, 100)); // Prepend new logs and keep max 100
    };

    eventSource.onerror = () => {
      setPollingLogs(prev => ['[ERROR] Log stream connection lost. Will attempt to reconnect.', ...prev].slice(0, 100));
      // The browser will automatically try to reconnect.
    };

    // Cleanup on component unmount
    return () => {
      eventSource.close();
    };
  }, []); // Empty dependency array ensures this runs only once on mount

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
    } catch (err) {
      setError('Failed to fetch incomplete tickets.');
    } finally {
      setLoadingIncomplete(false);
    }
  };

  const handleGenerateSolutions = async (ticketKey) => {
    setSelectedTicket(ticketKey);
    setGeneratingSolutions(true);
    setSolutions([]);
    try {
      const response = await axios.post(`/api/generate-solutions/${ticketKey}`);
      setSolutions(response.data.solutions);
    } catch (err) {
      setError(`Failed to generate solutions for ticket ${ticketKey}.`);
    } finally {
      setGeneratingSolutions(false);
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
    <Container fluid className="dashboard">
      <header className="dashboard-header">
        <Row>
          <Col>
            <h1><FaUserCog className="icon-space" /> LensOra AI Agent UI</h1>
            <p>Human-in-the-loop Validation and Resolution System for JIRA</p>
          </Col>
        </Row>
      </header>
      
      {successMessage && <Alert variant="success" onClose={() => setSuccessMessage(null)} dismissible><FaCheckCircle className="icon-space" /> {successMessage}</Alert>}
      {error && <Alert variant="danger" onClose={() => setError(null)} dismissible><FaExclamationCircle className="icon-space" /> {error}</Alert>}
      {uploadStatus.message && <Alert variant="success" onClose={() => setUploadStatus({ ...uploadStatus, message: '' })} dismissible>{uploadStatus.message}</Alert>}
      {uploadStatus.error && <Alert variant="danger" onClose={() => setUploadStatus({ ...uploadStatus, error: '' })} dismissible>{uploadStatus.error}</Alert>}

      <Tab.Container defaultActiveKey="dashboard" onSelect={(k) => setActiveTab(k)}>
        <Nav variant="tabs" className="mb-3">
          {/* --- NEW: Incomplete Tickets Tab --- */}
          <Nav.Item>
            <Nav.Link eventKey="incomplete"><FaTasks className="icon-space" />Incomplete Tickets</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="dashboard"><FaList className="icon-space" />Resolution Dashboard</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="admin"><FaBrain className="icon-space" />Knowledge Management</Nav.Link>
          </Nav.Item>
        </Nav>

        <Tab.Content>
          {/* --- NEW: Incomplete Tickets Pane --- */}
          <Tab.Pane eventKey="incomplete">
            <Row>
              <Col lg={6}>
                 <Card className="mb-4">
                  <Card.Header><h4><FaHistory className="icon-space" /> Live Polling Log</h4></Card.Header>
                  <Card.Body className="polling-log-viewer">
                    {pollingLogs.length > 0 ? pollingLogs.map((log, index) => (
                      <div key={index} className="log-entry">
                        <span className="log-message">{log}</span>
                      </div>
                    )) : <p className="text-muted">Waiting for polling service logs...</p>}
                  </Card.Body>
                </Card>
              </Col>
              <Col lg={6}>
                <Card>
                  <Card.Header>
                     <h4><FaExclamationCircle className="icon-space" /> Incomplete Tickets History</h4>
                     <Button variant="outline-primary" size="sm" onClick={fetchIncompleteTickets} disabled={loadingIncomplete}>
                      {loadingIncomplete ? <Spinner animation="border" size="sm" /> : 'Refresh'}
                    </Button>
                  </Card.Header>
                  <Card.Body className="tickets-list">
                    {loadingIncomplete ? (
                      <div className="text-center p-4"><Spinner animation="border" /><p className="mt-2">Loading tickets...</p></div>
                    ) : incompleteTickets.length > 0 ? (
                      incompleteTickets.map(ticket => (
                        <Card key={ticket.ticket_key} className="ticket-card mb-2 border-warning">
                          <Card.Body>
                            <div className="ticket-header">
                              <h5>{ticket.ticket_key}</h5>
                              <Badge bg="primary">{ticket.module}</Badge>
                            </div>
                            <p className="mb-1"><strong>Missing Fields:</strong> {ticket.missing_fields.join(', ')}</p>
                            <div className="ticket-meta">
                              <small>Last Validated: {formatDateTime(ticket.validated_at)}</small>
                              <small>Model: {ticket.llm_provider_model}</small>
                            </div>
                          </Card.Body>
                        </Card>
                      ))
                    ) : (
                      <div className="text-center p-4"><p>No incomplete tickets found.</p></div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab.Pane>

          <Tab.Pane eventKey="dashboard">
            <Row>
              <Col md={5} className="tickets-column">
                <Card>
                  <Card.Header>
                    <h4><FaCheckCircle className="icon-space" />Tickets Queue</h4>
                    <Button variant="outline-primary" size="sm" onClick={fetchCompleteTickets} disabled={loadingComplete}>
                      {loadingComplete ? <Spinner animation="border" size="sm" /> : 'Refresh'}
                    </Button>
                  </Card.Header>
                  <Card.Body className="tickets-list">
                    {loadingComplete ? (
                      <div className="text-center p-4"><Spinner animation="border" /><p className="mt-2">Loading tickets...</p></div>
                    ) : completeTickets.length > 0 ? (
                      completeTickets.map(ticket => (
                        <Card key={ticket.ticket_key} className={`ticket-card mb-2 ${selectedTicket === ticket.ticket_key ? 'selected' : ''}`}>
                          <Card.Body>
                            <div className="ticket-header"><h5>{ticket.ticket_key}</h5><Badge bg="info">{ticket.module}</Badge></div>
                            <div className="ticket-meta"><small>Validated: {formatDateTime(ticket.validated_at)}</small><small>Confidence: {(ticket.confidence * 100).toFixed(1)}%</small></div>
                            <div className="ticket-actions mt-2">
                              <Button variant="primary" size="sm" onClick={() => handleGenerateSolutions(ticket.ticket_key)} disabled={generatingSolutions && selectedTicket === ticket.ticket_key}>
                                {generatingSolutions && selectedTicket === ticket.ticket_key ? <><Spinner as="span" animation="border" size="sm" /> Generating...</> : <><FaSearch className="icon-space" /> Generate Solutions</>}
                              </Button>
                            </div>
                          </Card.Body>
                        </Card>
                      ))
                    ) : (
                      <div className="text-center p-4"><p>No complete tickets in the queue.</p></div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
              
              <Col md={7} className="solutions-column">
                <Card>
                  <Card.Header><h4>{selectedTicket ? `Solution Alternatives for ${selectedTicket}`: 'Select a ticket to view solutions'}</h4></Card.Header>
                  <Card.Body>
                    {generatingSolutions ? (
                      <div className="text-center p-5"><Spinner animation="border" /><p className="mt-3">Generating solutions...</p></div>
                    ) : solutions.length > 0 ? (
                      <div className="solutions-list">
                        {solutions.map((solution, index) => (
                          <Card key={index} className="solution-card mb-3"><Card.Header><div className="solution-header"><h5>Solution Alternative #{index + 1}</h5><div><Badge bg="success" className="me-2">Confidence: {(solution.confidence * 100).toFixed(1)}%</Badge><Badge bg="secondary">Model: {solution.llm_provider_model}</Badge></div></div></Card.Header><Card.Body><div className="solution-preview"><ReactMarkdown>{solution.solution_text.length > 250 ? `${solution.solution_text.substring(0, 250)}...` : solution.solution_text}</ReactMarkdown></div>{solution.sources && solution.sources.length > 0 && (<div className="solution-sources mt-2"><small><strong>Sources:</strong> {solution.sources.map(src => src.key || src).join(', ')}</small></div>)}<div className="solution-actions mt-3"><Button variant="success" onClick={() => handleReviewSolution(solution)}>Review & Submit</Button></div></Card.Body></Card>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center p-5"><p>Select a ticket and click "Generate Solutions".</p></div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab.Pane>

          <Tab.Pane eventKey="admin">
            <Row>
              <Col md={6}><Card><Card.Header><h4><FaBrain className="icon-space" /> Core Knowledge Base</h4></Card.Header><Card.Body><Card.Text>Upload a CSV or XLSX file to update the agent's core knowledge of ERP modules and their mandatory fields. The file must contain columns: <code>module_name</code> and <code>field_name</code>.</Card.Text><Form.Group controlId="formKnowledgeFile" className="mb-3"><Form.Label>Select Knowledge File</Form.Label><Form.Control type="file" accept=".csv, .xlsx" onChange={(e) => setKnowledgeFile(e.target.files[0])} /></Form.Group><Button variant="primary" onClick={() => handleFileUpload('knowledge')} disabled={uploadingKnowledge}>{uploadingKnowledge ? <><Spinner as="span" animation="border" size="sm" /> Uploading...</> : <><FaUpload className="icon-space" /> Upload Core Knowledge</>}</Button></Card.Body></Card></Col>
              <Col md={6}><Card><Card.Header><h4><FaBook className="icon-space" /> RAG Knowledge Base</h4></Card.Header><Card.Body><Card.Text>Upload a CSV or XLSX file of previously solved JIRA tickets to expand the agent's experiential knowledge. The file must contain columns: <code>ticket_key</code>, <code>summary</code>, and <code>resolution</code>.</Card.Text><Form.Group controlId="formRagFile" className="mb-3"><Form.Label>Select Solved Tickets File</Form.Label><Form.Control type="file" accept=".csv, .xlsx" onChange={(e) => setRagFile(e.target.files[0])} /></Form.Group><Button variant="primary" onClick={() => handleFileUpload('rag')} disabled={uploadingRag}>{uploadingRag ? <><Spinner as="span" animation="border" size="sm" /> Uploading...</> : <><FaUpload className="icon-space" /> Upload Solved Tickets</>}</Button></Card.Body></Card></Col>
            </Row>
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>
      
      <Modal show={showSolutionModal} onHide={() => setShowSolutionModal(false)} size="lg" centered>
        <Modal.Header closeButton><Modal.Title>Review Solution for {selectedTicket}</Modal.Title></Modal.Header>
        <Modal.Body>
          {selectedSolution && (
            <>
              <div className="solution-metadata mb-3"><Badge bg="success" className="me-2">Confidence: {(selectedSolution.confidence * 100).toFixed(1)}%</Badge><Badge bg="secondary">Model: {selectedSolution.llm_provider_model}</Badge>{selectedSolution.sources && selectedSolution.sources.length > 0 && (<div className="mt-2"><small><strong>Sources:</strong> {selectedSolution.sources.map(src => src.key || src).join(', ')}</small></div>)}</div>
              <h5>Original Suggestion:</h5>
              <div className="solution-content border p-3 bg-light"><ReactMarkdown>{selectedSolution.solution_text}</ReactMarkdown></div>
              <Form.Group className="mt-3" controlId="solutionTextArea">
                <Form.Label><strong>Edit and Finalize Response:</strong></Form.Label>
                <Form.Control as="textarea" rows={10} value={selectedSolution.solution_text} onChange={(e) => setSelectedSolution({...selectedSolution, solution_text: e.target.value})} />
              </Form.Group>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSolutionModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmitResolution} disabled={submittingResolution}>{submittingResolution ? <><Spinner as="span" animation="border" size="sm" /> Submitting...</> : <>Submit to JIRA</>}</Button>
        </Modal.Footer>
      </Modal>
      
      <footer className="dashboard-footer"><p>© 2025 LensOra AI | Human-in-the-loop Oracle ERP Resolution System</p></footer>
    </Container>
  );
}

export default App;
