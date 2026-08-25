import { useState } from 'react';
import DashboardHeader from './components/DashboardHeader';
import ChatPanel from './components/ChatPanel';
import DataPanel from './components/DataPanel';

export default function App() {
  // Signal to DataPanel to refresh after a chat answer (in case chat writes data — future-proofing)
  const [refreshSignal, setRefreshSignal] = useState(0);

  function handleNewAnswer() {
    // Optionally refresh the data panel after each answer
    setRefreshSignal(s => s + 1);
  }

  return (
    <div className="app-shell">
      <DashboardHeader />
      <div className="app-body">
        <ChatPanel onNewAnswer={handleNewAnswer} />
        <DataPanel refreshSignal={refreshSignal} />
      </div>
    </div>
  );
}
