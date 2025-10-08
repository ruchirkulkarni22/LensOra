import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#14b8a6', // teal-500 accent
      contrastText: '#fff',
    },
    secondary: {
      main: '#4f46e5', // indigo for secondary
      contrastText: '#fff',
    },
    background: {
      default: '#f1f5f9',
      paper: '#ffffff',
    },
    info: {
      main: '#64748b',
    },
    success: {
      main: '#22c55e',
    },
    warning: {
      main: '#f59e42',
    },
    error: {
      main: '#ef4444',
    },
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
    },
  },
  typography: {
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      styleOverrides: {
        containedPrimary: {
          backgroundColor: '#14b8a6',
          color: '#fff',
          '&:hover': {
            backgroundColor: '#0f766e',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          '&.confidence-badge': {
            backgroundColor: '#ccfbf1',
            color: '#0f766e',
            fontWeight: 500,
          },
        },
      },
    },
  },
});

export default theme;
