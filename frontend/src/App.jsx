import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import RightSidebar from './components/RightSidebar'; // Import
import { getChats, createChat } from './services/api';

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
      console.error("Failed to load chats", error);
    }
  };

  const handleNewChat = async () => {
    try {
      const newChat = await createChat("New Chat");
      setChats([newChat, ...chats]);
      setActiveChat(newChat);
    } catch (error) {
      console.error("Failed to create chat", error);
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
          onSelectChat={handleSelectChat}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
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
