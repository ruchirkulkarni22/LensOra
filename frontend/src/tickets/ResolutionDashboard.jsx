import React from 'react';
import { Card, CardHeader, CardContent, Typography, Chip, Button, Box, Divider, CircularProgress, IconButton } from '@mui/material';
import { FaSync, FaExternalLinkAlt } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';

export default function ResolutionDashboard({
  tickets, loadingTickets, selectedTicket, onGenerate, generatingSolutions,
  solutions, formatDateTime, onReviewSolution, onSelectTicket, hasCachedSolutions
}) {
  return (
    <div className="grid md:grid-cols-12 gap-6">
      <Card className="md:col-span-5" variant="outlined">
        <CardHeader 
          title={
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="w-2 h-2 rounded-full bg-teal-500 mr-2.5"></span>
                <Typography variant="h6" className="text-slate-800">Tickets Queue</Typography>
              </div>
              <IconButton 
                size="small" 
                color="primary" 
                onClick={() => onGenerate(null)} 
                disabled={loadingTickets}
                aria-label="Refresh tickets"
                className="transition-all duration-300 ease-in-out"
                sx={{ 
                  width: '34px', 
                  height: '34px', 
                  backgroundColor: loadingTickets ? 'rgba(20, 184, 166, 0.05)' : 'rgba(20, 184, 166, 0.1)',
                  '&:hover': {
                    backgroundColor: 'rgba(20, 184, 166, 0.2)'
                  }
                }}
              >
                {loadingTickets ? (
                  <div className="animate-spin">
                    <CircularProgress size={16} thickness={4} />
                  </div>
                ) : (
                  <FaSync className="text-teal-600" />
                )}
              </IconButton>
            </div>
          }
          sx={{ backgroundColor: 'rgba(241, 245, 249, 0.5)' }}
        />
        <Divider />
        <CardContent className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
          {loadingTickets && (
            <div className="flex flex-col items-center justify-center h-48 py-6">
              <CircularProgress color="primary" size={32} />
              <p className="mt-4 text-sm font-medium text-slate-600">Loading tickets...</p>
            </div>
          )}
          {!loadingTickets && tickets.length === 0 && (
            <div className="flex flex-col items-center justify-center h-48 text-center px-4">
              <div className="text-slate-400 mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <Typography variant="body1" className="font-medium text-slate-600">No complete tickets available</Typography>
              <Typography variant="body2" className="mt-2 text-slate-500">Valid tickets with all required fields will appear here</Typography>
            </div>
          )}
          {!loadingTickets && tickets.map(t => {
            const isSelected = selectedTicket === t.ticket_key;
            return (
              <Box 
                key={t.ticket_key} 
                className={`border rounded-lg p-4 transition bg-white shadow-sm hover:shadow-md cursor-pointer ${isSelected ? 'ring-2 ring-teal-500 bg-teal-50/70' : 'hover:border-teal-200'}`}
                onClick={() => onSelectTicket(t.ticket_key)}
                role="button"
                tabIndex={0}
                aria-selected={isSelected}
                aria-label={`Ticket ${t.ticket_key}`}
                onKeyDown={(e) => e.key === 'Enter' && onSelectTicket(t.ticket_key)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Typography variant="h6" className="font-semibold text-slate-800">{t.ticket_key}</Typography>
                    <IconButton 
                      size="small" 
                      color="primary" 
                      href={`https://calfusproducts.atlassian.net/browse/${t.ticket_key}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-1"
                      aria-label={`View ticket ${t.ticket_key} in JIRA`}
                      onClick={(e) => e.stopPropagation()} // Prevent the ticket selection when clicking the link
                    >
                      <FaExternalLinkAlt size={12} />
                    </IconButton>
                  </div>
                  <Chip 
                    label={t.module} 
                    size="small" 
                    color="info"
                    className="font-medium"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 mb-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-1">Validated:</span> 
                    <span>{formatDateTime(t.validated_at)}</span>
                  </div>
                  <div className="flex items-center justify-end">
                    <span className="font-medium mr-1">Confidence:</span>
                    <span className={`${parseInt((t.confidence * 100)) >= 80 ? 'text-emerald-600' : parseInt((t.confidence * 100)) >= 50 ? 'text-amber-600' : 'text-red-600'} font-medium`}>
                      {(t.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="flex justify-start mt-4">
                  <Button 
                    size="small" 
                    variant="contained" 
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent ticket selection when clicking the button
                      onGenerate(t.ticket_key);
                    }} 
                    disabled={generatingSolutions && isSelected}
                    color={hasCachedSolutions(t.ticket_key) ? "info" : "primary"}
                    className="font-medium px-4 py-1"
                    disableElevation
                    startIcon={generatingSolutions && isSelected ? <CircularProgress size={14} color="inherit" /> : null}
                    aria-label={generatingSolutions && isSelected ? 'Generating solutions' : hasCachedSolutions(t.ticket_key) ? 'Regenerate solutions' : 'Generate solutions'}
                  >
                    {generatingSolutions && isSelected ? 'Generating...' : 
                     hasCachedSolutions(t.ticket_key) ? 'Regenerate Solutions' : 'Generate Solutions'}
                  </Button>
                </div>
              </Box>
            );
          })}
        </CardContent>
      </Card>

      <Card className="md:col-span-7" variant="outlined" sx={{ display: 'flex', flexDirection: 'column' }}>
        <CardHeader 
          title={
            <div className="flex justify-between items-center">
              <Typography variant="h6" className="text-slate-800">
                {selectedTicket ? `Solutions for ${selectedTicket}` : 'Select a ticket'}
              </Typography>
              {hasCachedSolutions(selectedTicket) && !generatingSolutions && 
                <Chip 
                  size="small" 
                  color="success" 
                  label="Cached Solutions" 
                  className="ml-2 font-medium"
                  icon={<span className="w-2 h-2 rounded-full bg-green-500 mx-1"></span>}
                />
              }
            </div>
          }
          sx={{ backgroundColor: 'rgba(241, 245, 249, 0.5)' }}
        />
        <Divider />
        <CardContent className="max-h-[70vh] overflow-y-auto space-y-4 flex-1">
          {generatingSolutions && (
            <div className="flex flex-col items-center justify-center h-64 py-10">
              <div className="relative">
                <CircularProgress 
                  color="primary" 
                  size={40} 
                  thickness={4}
                  className="z-10" 
                />
                <div className="absolute top-0 left-0 right-0 bottom-0 flex items-center justify-center">
                  <span className="text-xs font-medium text-primary">AI</span>
                </div>
              </div>
              <p className="mt-4 text-sm font-medium text-slate-600">Generating solutions...</p>
              <p className="text-xs text-slate-500 max-w-xs text-center mt-2">
                Our AI is analyzing the ticket and finding the best solutions based on historical data
              </p>
            </div>
          )}
          {!generatingSolutions && solutions.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 text-center px-4">
              <div className="text-slate-400 mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <Typography variant="body1" className="font-medium text-slate-600">Select a ticket and click Generate Solutions</Typography>
              <Typography variant="body2" className="mt-2 text-slate-500">Solutions will appear here once generated</Typography>
            </div>
          )}
          {!generatingSolutions && solutions.map((s, i) => (
            <Box key={i} className="border rounded-lg overflow-hidden shadow-sm bg-white hover:shadow transition-shadow">
              <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b">
                <div className="flex items-center">
                  <div className="w-6 h-6 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-2 font-medium text-sm">
                    {i + 1}
                  </div>
                  <Typography variant="subtitle1" className="font-medium">Solution #{i + 1}</Typography>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center">
                    <span className="font-medium text-slate-600 mr-1">Confidence:</span>
                    <span className={`${parseInt((s.confidence * 100)) >= 80 ? 'text-emerald-600' : parseInt((s.confidence * 100)) >= 50 ? 'text-amber-600' : 'text-red-600'} font-medium`}>
                      {(s.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Chip 
                    label={s.llm_provider_model} 
                    size="small" 
                    variant="outlined" 
                    className="font-medium"
                  />
                </div>
              </div>
              <div className="p-5 prose prose-sm max-w-none prose-headings:font-medium prose-headings:text-slate-800">
                <ReactMarkdown>{s.solution_text}</ReactMarkdown>
                {s.sources?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <p className="text-xs text-slate-500">
                      <strong className="font-medium">Sources:</strong> {s.sources.map(src => src.key || src).join(', ')}
                    </p>
                  </div>
                )}
                <div className="mt-4 pt-2 flex justify-end">
                  <Button 
                    size="medium" 
                    variant="contained" 
                    color="primary" 
                    onClick={() => onReviewSolution(s)}
                    disableElevation
                    className="font-medium"
                    aria-label="Review and submit this solution"
                  >
                    Review & Submit
                  </Button>
                </div>
              </div>
            </Box>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
