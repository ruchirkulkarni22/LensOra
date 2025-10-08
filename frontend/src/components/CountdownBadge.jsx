import React from 'react';
import { Chip } from '@mui/material';

export default function CountdownBadge({ countdown }) {
  return (
    <Chip size="small" color="secondary" variant="outlined" label={`Next Poll: ${countdown || '...'}`} />
  );
}
