import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Default to dark mode unless user has explicitly chosen light
const stored = localStorage.getItem('marta-theme');
if (stored === 'light') {
  document.documentElement.classList.remove('dark');
} else {
  document.documentElement.classList.add('dark');
}

createRoot(document.getElementById("root")!).render(<App />);
