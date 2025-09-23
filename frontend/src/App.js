// File: frontend/src/App.js
import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Badge, Button, Spinner, Alert, Modal, Form, Tab, Nav } from 'react-bootstrap';
import axios from 'axios';
import { FaCheckCircle, FaExclamationCircle, FaList, FaSearch, FaUserCog, FaUpload, FaBrain, FaBook } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  // State variables for main dashboard
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [solutions, setSolutions] = useState([]);
  const [generatingSolutions, setGeneratingSolutions] = useState(false);
  const [showSolutionModal, setShowSolutionModal] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);
  const [submittingResolution, setSubmittingResolution] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  // --- NEW: State variables for file uploads ---
  const [knowledgeFile, setKnowledgeFile] = useState(null);
  const [ragFile, setRagFile] = useState(null);
  const [uploadingKnowledge, setUploadingKnowledge] = useState(false);
  const [uploadingRag, setUploadingRag] = useState(false);
  const [uploadStatus, setUploadStatus] = useState({ success: false, message: '', error: '' });


  // Fetch complete tickets on component mount
  useEffect(() => {
    fetchCompleteTickets();
  }, []);
  
  // Function to fetch complete tickets from the API
  const fetchCompleteTickets = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/complete-tickets');
      setTickets(response.data.tickets);
    } catch (err) {
      setError('Failed to fetch tickets. Please try again later.');
      console.error('Error fetching tickets:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Function to generate solutions for a selected ticket
  const handleGenerateSolutions = async (ticketKey) => {
    setSelectedTicket(ticketKey);
    setGeneratingSolutions(true);
    setSolutions([]);
    
    try {
      const response = await axios.post(`/api/generate-solutions/${ticketKey}`);
      // The backend now returns a dictionary with a 'solutions' key
      setSolutions(response.data.solutions);
    } catch (err) {
      setError(`Failed to generate solutions for ticket ${ticketKey}. Please try again.`);
      console.error('Error generating solutions:', err);
    } finally {
      setGeneratingSolutions(false);
    }
  };
  
  // Function to open the solution review modal
  const handleReviewSolution = (solution) => {
    setSelectedSolution(solution);
    setShowSolutionModal(true);
  };
  
  // Function to submit a resolution to JIRA
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
      
      // Remove the resolved ticket from the list
      setTickets(tickets.filter(ticket => ticket.ticket_key !== selectedTicket));
      
      // Reset state
      setSelectedTicket(null);
      setSolutions([]);
    } catch (err) {
      setError(`Failed to post solution to ticket ${selectedTicket}. Please try again.`);
      console.error('Error posting solution:', err);
    } finally {
      setSubmittingResolution(false);
    }
  };

  // --- NEW: Function to handle file uploads ---
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
      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setUploadStatus({ success: true, message: response.data.message, error: '' });
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'An unexpected error occurred.';
      setUploadStatus({ success: false, message: '', error: `Upload failed: ${errorMessage}` });
      console.error(`Error uploading ${fileType} file:`, err);
    } finally {
      setUploading(false);
    }
  };

  
  // Function to format date/time
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return 'N/A';
    const date = new Date(dateTimeStr);
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(date);
  };
  
  return (
    <Container fluid className="dashboard">
      <header className="dashboard-header">
        <Row>
          <Col>
            <h1><FaUserCog className="icon-space" /> LensOra AI Resolution Dashboard</h1>
            <p>Human-in-the-loop resolution system for JIRA tickets</p>
          </Col>
        </Row>
      </header>
      
      {/* Success/Error Message Alerts */}
      {successMessage && <Alert variant="success" onClose={() => setSuccessMessage(null)} dismissible><FaCheckCircle className="icon-space" /> {successMessage}</Alert>}
      {error && <Alert variant="danger" onClose={() => setError(null)} dismissible><FaExclamationCircle className="icon-space" /> {error}</Alert>}
      {uploadStatus.message && <Alert variant="success" onClose={() => setUploadStatus({ ...uploadStatus, message: '' })} dismissible>{uploadStatus.message}</Alert>}
      {uploadStatus.error && <Alert variant="danger" onClose={() => setUploadStatus({ ...uploadStatus, error: '' })} dismissible>{uploadStatus.error}</Alert>}

      <Tab.Container defaultActiveKey="dashboard">
        <Nav variant="tabs" className="mb-3">
          <Nav.Item>
            <Nav.Link eventKey="dashboard"><FaList className="icon-space" />Resolution Dashboard</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="admin"><FaBrain className="icon-space" />Knowledge Management</Nav.Link>
          </Nav.Item>
        </Nav>

        <Tab.Content>
          <Tab.Pane eventKey="dashboard">
            <Row>
              <Col md={5} className="tickets-column">
                <Card>
                  <Card.Header>
                    <h4><FaList className="icon-space" /> Complete Tickets Queue</h4>
                    <Button variant="outline-primary" size="sm" onClick={fetchCompleteTickets} disabled={loading}>
                      {loading ? <Spinner animation="border" size="sm" /> : 'Refresh'}
                    </Button>
                  </Card.Header>
                  <Card.Body className="tickets-list">
                    {loading ? (
                      <div className="text-center p-4"><Spinner animation="border" /><p className="mt-2">Loading tickets...</p></div>
                    ) : tickets.length > 0 ? (
                      tickets.map(ticket => (
                        <Card key={ticket.ticket_key} className={`ticket-card mb-2 ${selectedTicket === ticket.ticket_key ? 'selected' : ''}`}>
                          <Card.Body>
                            <div className="ticket-header">
                              <h5>{ticket.ticket_key}</h5>
                              <Badge bg="info">{ticket.module}</Badge>
                            </div>
                            <div className="ticket-meta">
                              <small>Validated: {formatDateTime(ticket.validated_at)}</small>
                              <small>Confidence: {(ticket.confidence * 100).toFixed(1)}%</small>
                            </div>
                            <div className="ticket-actions mt-2">
                              <Button variant="primary" size="sm" onClick={() => handleGenerateSolutions(ticket.ticket_key)} disabled={generatingSolutions && selectedTicket === ticket.ticket_key}>
                                {generatingSolutions && selectedTicket === ticket.ticket_key ? (
                                  <><Spinner animation="border" size="sm" className="icon-space" /> Generating...</>
                                ) : (
                                  <><FaSearch className="icon-space" /> Generate Solutions</>
                                )}
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
                          <Card key={index} className="solution-card mb-3">
                            <Card.Header>
                              <div className="solution-header">
                                <h5>Solution Alternative #{index + 1}</h5>
                                <div>
                                  <Badge bg="success" className="me-2">Confidence: {(solution.confidence * 100).toFixed(1)}%</Badge>
                                  <Badge bg="secondary">Model: {solution.llm_provider_model}</Badge>
                                </div>
                              </div>
                            </Card.Header>
                            <Card.Body>
                              <div className="solution-preview"><ReactMarkdown>{solution.solution_text.length > 250 ? `${solution.solution_text.substring(0, 250)}...` : solution.solution_text}</ReactMarkdown></div>
                              {solution.sources && solution.sources.length > 0 && (<div className="solution-sources mt-2"><small><strong>Sources:</strong> {solution.sources.map(src => src.key || src).join(', ')}</small></div>)}
                              <div className="solution-actions mt-3"><Button variant="success" onClick={() => handleReviewSolution(solution)}>Review & Submit</Button></div>
                            </Card.Body>
                          </Card>
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

          {/* --- NEW: Admin Panel Tab --- */}
          <Tab.Pane eventKey="admin">
            <Row>
              <Col md={6}>
                <Card>
                  <Card.Header>
                    <h4><FaBrain className="icon-space" /> Core Knowledge Base</h4>
                  </Card.Header>
                  <Card.Body>
                    <Card.Text>
                      Upload a CSV or XLSX file to update the agent's core knowledge of ERP modules and their mandatory fields. The file must contain columns: <code>module_name</code> and <code>field_name</code>.
                    </Card.Text>
                    <Form.Group controlId="formKnowledgeFile" className="mb-3">
                      <Form.Label>Select Knowledge File</Form.Label>
                      <Form.Control type="file" accept=".csv, .xlsx" onChange={(e) => setKnowledgeFile(e.target.files[0])} />
                    </Form.Group>
                    <Button variant="primary" onClick={() => handleFileUpload('knowledge')} disabled={uploadingKnowledge}>
                      {uploadingKnowledge ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Uploading...</> : <><FaUpload className="icon-space" /> Upload Core Knowledge</>}
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={6}>
                <Card>
                  <Card.Header>
                    <h4><FaBook className="icon-space" /> RAG Knowledge Base</h4>
                  </Card.Header>
                  <Card.Body>
                    <Card.Text>
                      Upload a CSV or XLSX file of previously solved JIRA tickets to expand the agent's experiential knowledge. The file must contain columns: <code>ticket_key</code>, <code>summary</code>, and <code>resolution</code>.
                    </Card.Text>
                    <Form.Group controlId="formRagFile" className="mb-3">
                      <Form.Label>Select Solved Tickets File</Form.Label>
                      <Form.Control type="file" accept=".csv, .xlsx" onChange={(e) => setRagFile(e.target.files[0])} />
                    </Form.Group>
                    <Button variant="primary" onClick={() => handleFileUpload('rag')} disabled={uploadingRag}>
                      {uploadingRag ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Uploading...</> : <><FaUpload className="icon-space" /> Upload Solved Tickets</>}
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>
      
      {/* Solution Review Modal */}
      <Modal show={showSolutionModal} onHide={() => setShowSolutionModal(false)} size="lg" centered>
        <Modal.Header closeButton><Modal.Title>Review Solution for {selectedTicket}</Modal.Title></Modal.Header>
        <Modal.Body>
          {selectedSolution && (
            <>
              <div className="solution-metadata mb-3">
                <Badge bg="success" className="me-2">Confidence: {(selectedSolution.confidence * 100).toFixed(1)}%</Badge>
                <Badge bg="secondary">Model: {selectedSolution.llm_provider_model}</Badge>
                {selectedSolution.sources && selectedSolution.sources.length > 0 && (<div className="mt-2"><small><strong>Sources:</strong> {selectedSolution.sources.map(src => src.key || src).join(', ')}</small></div>)}
              </div>
              <h5>Solution Content:</h5>
              <div className="solution-content border p-3 bg-light"><ReactMarkdown>{selectedSolution.solution_text}</ReactMarkdown></div>
              <Alert variant="info" className="mt-3"><FaExclamationCircle className="icon-space" /> Review and edit the solution above before submitting.</Alert>
              <textarea className="form-control mt-3" rows="10" value={selectedSolution.solution_text} onChange={(e) => setSelectedSolution({...selectedSolution, solution_text: e.target.value})} />
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSolutionModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmitResolution} disabled={submittingResolution}>
            {submittingResolution ? <><Spinner animation="border" size="sm" className="icon-space" /> Submitting...</> : <>Submit to JIRA</>}
          </Button>
        </Modal.Footer>
      </Modal>
      
      <footer className="dashboard-footer">
        <p>© 2025 LensOra AI | Human-in-the-loop Oracle ERP Resolution System</p>
      </footer>
    </Container>
  );
}

export default App;
