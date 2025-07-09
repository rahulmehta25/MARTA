import React from 'react';
import { MainLayout } from './components/layout/MainLayout';
import { config, validateConfig } from './utils/config';
import './App.css';

function App() {
  // Validate configuration on app start
  React.useEffect(() => {
    validateConfig();
  }, []);

  return (
    <div className="App">
      <MainLayout />
    </div>
  );
}

export default App;
