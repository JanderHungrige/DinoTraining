import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
// Doc 78: Lato, bundled — the app runs offline and never asks Google for a font.
import '@fontsource/lato/latin-400.css';
import '@fontsource/lato/latin-400-italic.css';
import '@fontsource/lato/latin-700.css';
import './styles.css';
import './look.css';
import './sketch.css';

const container = document.getElementById('root');
if (!container) {
  // index.html is ours; a missing #root means the bundle was loaded by something else.
  throw new Error('Root element #root not found — cannot mount V-Rex.');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
