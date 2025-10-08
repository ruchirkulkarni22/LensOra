import React from 'react';
import { Card, CardHeader, CardContent, Typography, Button, Stack, TextField, CircularProgress } from '@mui/material';
import { FaUpload } from 'react-icons/fa';

export default function KnowledgeUpload({
  onUploadKnowledge, onUploadRag,
  knowledgeFile, setKnowledgeFile,
  ragFile, setRagFile,
  uploadingKnowledge, uploadingRag
}) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card variant="outlined">
        <CardHeader title="Field Structure Knowledge" />
        <CardContent className="space-y-4">
          <Typography variant="body2">
            Upload CSV/XLSX containing field structure information with required columns: 
            <span className="font-medium text-teal-700"> module_name</span> and 
            <span className="font-medium text-teal-700"> field_name</span>.
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <Button component="label" variant="outlined" size="small" color="primary">
              Select File
              <input type="file" accept=".csv,.xlsx" hidden onChange={(e) => setKnowledgeFile(e.target.files[0])} />
            </Button>
            <TextField size="small" value={knowledgeFile?.name || ''} placeholder="No file selected" InputProps={{ readOnly: true }} />
          </Stack>
          <Button 
            onClick={onUploadKnowledge} 
            variant="contained" 
            color="primary" 
            startIcon={!uploadingKnowledge && <FaUpload />} 
            disabled={uploadingKnowledge}
            className="relative overflow-hidden"
            sx={{
              '&:disabled': {
                backgroundColor: 'rgba(20, 184, 166, 0.8)',
                color: 'white'
              }
            }}
          >
            {uploadingKnowledge ? (
              <span className="flex items-center">
                <CircularProgress size={18} color="inherit" thickness={4} className="mr-2" />
                <span>Processing...</span>
              </span>
            ) : 'Upload Structure Data'}
          </Button>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardHeader title="Historical Solutions" />
        <CardContent className="space-y-4">
          <Typography variant="body2">
            Upload previously solved tickets in CSV/XLSX format with required columns: 
            <span className="font-medium text-teal-700"> ticket_key</span>, 
            <span className="font-medium text-teal-700"> summary</span>, and 
            <span className="font-medium text-teal-700"> resolution</span>.
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <Button component="label" variant="outlined" size="small" color="primary">
              Select File
              <input type="file" accept=".csv,.xlsx" hidden onChange={(e) => setRagFile(e.target.files[0])} />
            </Button>
            <TextField size="small" value={ragFile?.name || ''} placeholder="No file selected" InputProps={{ readOnly: true }} />
          </Stack>
          <Button 
            onClick={onUploadRag} 
            variant="contained" 
            color="primary" 
            startIcon={!uploadingRag && <FaUpload />} 
            disabled={uploadingRag}
            className="relative overflow-hidden"
            sx={{
              '&:disabled': {
                backgroundColor: 'rgba(20, 184, 166, 0.8)',
                color: 'white'
              }
            }}
          >
            {uploadingRag ? (
              <span className="flex items-center">
                <CircularProgress size={18} color="inherit" thickness={4} className="mr-2" />
                <span>Processing...</span>
              </span>
            ) : 'Upload Historical Data'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
