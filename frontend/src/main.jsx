import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import './styles.css'
import './agent.css'
import './draw.css'
import './ritualModal.css'
import './verdict.css'
import './followup.css'
import './cardLibrary.css'
import './introVeil.css'
import './auth.css'
import './modelSettings.css'
import './refine.css'   /* 视觉精修层：必须最后加载 */

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
