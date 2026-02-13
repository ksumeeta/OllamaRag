import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import RightSidebar from './components/RightSidebar'; // Import
import { getChats, createChat, deleteChat } from './services/api';

/**
 * Main Application Component.
 * Manages chat state, sidebar visibility, and backend connection status.
 */
function App() {
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightSidebarOpen] = useState(true); // Permanent open

  // Context Flags State - Persisted
  const [contextFlags, setContextFlags] = useState(() => {
    const saved = localStorage.getItem('contextFlags');
    return saved ? JSON.parse(saved) : {
      useLLMData: true,
      useDocuments: true,
      useWebSearch: false
    };
  });

  const [backendOnline, setBackendOnline] = useState(false);
  const [overwriteMode, setOverwriteMode] = useState(false);

  const checkBackendStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/');
      if (response.ok) {
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (e) {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 60000); // Check every 60 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    localStorage.setItem('contextFlags', JSON.stringify(contextFlags));
  }, [contextFlags]);

  useEffect(() => {
    fetchChats();
  }, []);

  const fetchChats = async () => {
    try {
      const data = await getChats({ limit: 50 });
      setChats(data);
    } catch (error) {
      // Silently fail or use a UI notification
    }
  };

  const handleNewChat = async () => {
    try {
      const newChat = await createChat("New Chat");
      setChats([newChat, ...chats]);
      setActiveChat(newChat);
    } catch (error) {
      // handle error
    }
  };

  const handleDeleteChat = async (chatId) => {
    if (window.confirm("Are you sure you want to delete this chat? This action cannot be undone.")) {
      try {
        await deleteChat(chatId);
        if (activeChat?.id === chatId) {
          setActiveChat(null);
        }
        fetchChats();
      } catch (error) {
        // handle error
      }
    }
  };

  const handleSelectChat = (chat) => {
    setActiveChat(chat);
  };

  const refreshChats = () => {
    fetchChats();
  };

  return (
    <Router>
      <div className="flex h-screen bg-background text-foreground overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          chats={chats}
          activeChat={activeChat}
          onNewChat={handleNewChat}
          onDeleteChat={handleDeleteChat}
          onSelectChat={handleSelectChat}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          backendOnline={backendOnline}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 relative">

          {activeChat ? (
            <div className="flex h-full">
              <div className="flex-1 flex flex-col min-w-0">
                <ChatInterface
                  chat={activeChat}
                  onChatUpdate={refreshChats}
                  contextFlags={contextFlags} // Pass flags
                  overwriteMode={overwriteMode}
                // toggleRightSidebar removed
                />
              </div>

              {/* Right Sidebar */}
              <RightSidebar
                isOpen={rightSidebarOpen}
                contextFlags={contextFlags}
                setContextFlags={setContextFlags}
                chatId={activeChat?.id}
                attachments={activeChat?.attachments}
                overwriteMode={overwriteMode}
                setOverwriteMode={setOverwriteMode}
              />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-muted-foreground flex-col">
              <h1 className="text-4xl font-bold mb-4">Local LLM Workspace</h1>
              <p>Select a chat or create a new one to get started.</p>
              <button
                onClick={handleNewChat}
                className="mt-6 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
              >
                Start New Chat
              </button>
            </div>
          )}
        </div>
      </div>
    </Router>
  );
}

export default App;
