import React from 'react';
import { Card, CardHeader, CardContent, Typography, Chip, Box, Divider, IconButton } from '@mui/material';
import { FaExternalLinkAlt } from 'react-icons/fa';

export default function IncompleteTickets({ loading, tickets, countdown, formatDateTime }) {
  return (
    <Card variant="outlined" className="h-full">
      <CardHeader 
        title={
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center">
              <span className="w-2 h-2 rounded-full bg-amber-500 mr-2.5"></span>
              <Typography variant="h6" className="text-slate-800">Incomplete Tickets</Typography>
            </div>
            <div className="flex items-center">
              <Chip 
                size="small" 
                label={
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-teal-500 animate-ping absolute opacity-75"></span>
                    <span className="w-2 h-2 rounded-full bg-teal-500 relative"></span>
                    <span>Next Poll: {countdown || '...'}</span>
                  </div>
                }
                color="primary" 
                variant="outlined" 
                className="animate-pulse"
                sx={{ 
                  '& .MuiChip-label': { 
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center'
                  }
                }}
              />
            </div>
          </div>
        } 
        sx={{ backgroundColor: 'rgba(241, 245, 249, 0.5)' }}
      />
      <Divider />
      <CardContent className="space-y-3 max-h-[70vh] overflow-y-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center h-48 py-6">
            <div className="relative">
              <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
              <div className="absolute top-0 left-0 right-0 bottom-0 flex items-center justify-center">
                <span className="text-[10px] font-medium text-amber-500">JIRA</span>
              </div>
            </div>
            <p className="mt-4 text-sm font-medium text-slate-600">Loading tickets from JIRA...</p>
          </div>
        )}
        {!loading && tickets.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-center px-4">
            <div className="text-slate-400 mb-3">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <Typography variant="body1" className="font-medium text-slate-600">No incomplete tickets</Typography>
            <Typography variant="body2" className="mt-2 text-slate-500">All tickets have been properly validated</Typography>
          </div>
        )}
        {!loading && tickets.map(t => (
          <Box 
            key={t.ticket_key} 
            className="border rounded-lg p-4 bg-amber-50/70 border-amber-200 shadow-sm hover:shadow-md transition-shadow"
            role="region"
            aria-label={`Incomplete ticket ${t.ticket_key}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center">
                <Typography variant="subtitle1" className="font-semibold text-amber-900">{t.ticket_key}</Typography>
                <IconButton 
                  size="small" 
                  color="primary" 
                  href={`https://calfusproducts.atlassian.net/browse/${t.ticket_key}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-1"
                  aria-label={`View ticket ${t.ticket_key} in JIRA`}
                >
                  <FaExternalLinkAlt size={12} />
                </IconButton>
              </div>
              <Chip 
                label={t.module} 
                size="small" 
                color="primary" 
                className="font-medium"
              />
            </div>
            <div className="rounded-md bg-amber-100/70 border border-amber-200 p-3 mb-2">
              <Typography variant="body2" className="text-amber-900 flex items-start">
                <strong className="font-medium mr-1.5 whitespace-nowrap">Missing:</strong> 
                <span className="text-amber-800">{t.missing_fields.join(', ')}</span>
              </Typography>
            </div>
            <div className="flex justify-between text-xs text-slate-600 pt-1">
              <div className="flex items-center">
                <span className="font-medium mr-1">Validated:</span> 
                <span>{formatDateTime(t.validated_at)}</span>
              </div>
              <div className="flex items-center">
                <span className="font-medium text-amber-700">{t.llm_provider_model}</span>
              </div>
            </div>
          </Box>
        ))}
      </CardContent>
    </Card>
  );
}
