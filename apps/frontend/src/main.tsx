import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import './styles.css';

const container = document.getElementById('root');
if (!container) {
  // index.html is ours; a missing #root means the bundle was loaded by something else.
  throw new Error('Root element #root not found — cannot mount DinoTraining.');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
