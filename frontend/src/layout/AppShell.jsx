import React from 'react';
import { AppBar, Toolbar, Typography, Tabs, Tab, Box } from '@mui/material';
import { FaCheckCircle, FaExclamationTriangle, FaBrain } from 'react-icons/fa';

const TabLabel = ({ icon: Icon, label }) => (
  <span className="inline-flex items-center gap-2"><Icon size={16} /> {label}</span>
);

export default function AppShell({ value, onChange, children }) {
  return (
    <Box className="min-h-screen flex flex-col">
  <AppBar 
        position="static" 
        sx={{ 
          backgroundColor: '#14b8a6', 
          color: '#fff', 
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)' 
        }}
        className="transition-all duration-200"
      >
        <Toolbar className="flex flex-col md:flex-row md:justify-between md:items-center gap-2 py-3 container mx-auto px-4">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-lg bg-white/20 mr-2 flex items-center justify-center text-white">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <Typography variant="h5" className="font-semibold flex items-center gap-2">
                AssistIQ
              </Typography>
              <Typography variant="body2" className="opacity-90">
                Automated Support for JIRA Tickets
              </Typography>
            </div>
          </div>
          <Tabs
            value={value}
            onChange={(e, v) => onChange(v)}
            textColor="inherit"
            indicatorColor="secondary"
            variant="scrollable"
            allowScrollButtonsMobile
            aria-label="Navigation tabs"
            sx={{
              '& .MuiTabs-indicator': {
                height: '3px',
                borderRadius: '3px 3px 0 0'
              },
              '& .MuiTab-root': {
                minWidth: '100px',
                fontWeight: 500
              }
            }}
          >
            <Tab 
              value="incomplete" 
              label={<TabLabel icon={FaExclamationTriangle} label="Incomplete" />} 
              aria-label="Incomplete tickets tab"
            />
            <Tab 
              value="dashboard" 
              label={<TabLabel icon={FaCheckCircle} label="Resolution" />} 
              aria-label="Resolution dashboard tab"
            />
            <Tab 
              value="admin" 
              label={<TabLabel icon={FaBrain} label="Knowledge" />} 
              aria-label="Knowledge management tab"
            />
          </Tabs>
        </Toolbar>
      </AppBar>
      <Box component="main" className="flex-1 p-4 md:p-6 container mx-auto">{children}</Box>
      <footer className="text-center text-xs text-slate-500 py-4 border-t bg-white/60 backdrop-blur">
        <div className="container mx-auto">
          © 2025 AssistIQ | Automated Support Assistant
        </div>
      </footer>
    </Box>
  );
}


