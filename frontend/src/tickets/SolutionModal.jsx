import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Chip, Typography, TextField, Stack } from '@mui/material';
import ReactMarkdown from 'react-markdown';

export default function SolutionModal({ open, onClose, ticketKey, solution, onChange, onSubmit, submitting }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Review Solution for {ticketKey}</DialogTitle>
      <DialogContent dividers className="space-y-4">
        {solution && (
          <>
            <Stack direction="row" spacing={1} flexWrap="wrap" className="text-xs">
              <Chip label={`Confidence ${(solution.confidence * 100).toFixed(1)}%`} color="success" size="small" />
              <Chip label={solution.llm_provider_model} size="small" variant="outlined" />
            </Stack>
            {solution.sources?.length > 0 && (
              <Typography variant="caption" color="text.secondary">Sources: {solution.sources.map(src => src.key || src).join(', ')}</Typography>
            )}
            <div className="border rounded-md bg-slate-50 p-3 max-h-64 overflow-y-auto prose prose-sm">
              <ReactMarkdown>{solution.solution_text}</ReactMarkdown>
            </div>
            <TextField
              label="Edit and Finalize Response"
              multiline
              minRows={8}
              fullWidth
              value={solution.solution_text}
              onChange={(e) => onChange({ ...solution, solution_text: e.target.value })}
            />
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="text">Cancel</Button>
        <Button onClick={onSubmit} variant="contained" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit to JIRA'}</Button>
      </DialogActions>
    </Dialog>
  );
}
