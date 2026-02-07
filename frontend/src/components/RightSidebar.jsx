import React, { useState } from 'react';
import { X, Search, FileText, Globe, Database, Cpu, ChevronRight, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const RightSidebar = ({
    isOpen,
    // onClose, // Removed as it is permanent
    contextFlags,
    setContextFlags,
    chatId,
    attachments = []
}) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [selectedContext, setSelectedContext] = useState(null); // For Modal

    const handleSearch = async () => {
        if (!searchQuery.trim() || !chatId) return;
        setIsSearching(true);
        try {
            const response = await fetch('http://localhost:8000/api/chats/search_context', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chatId,
                    content: searchQuery,
                    role: 'user' // dummy
                })
            });
            if (response.ok) {
                const data = await response.json();
                setSearchResults(data);
            }
        } catch (error) {
            console.error("Search failed", error);
        } finally {
            setIsSearching(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="w-80 h-full border-l border-border bg-card flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border flex justify-between items-center">
                <h2 className="font-semibold text-foreground">Context Control</h2>
                {/* Close Button Removed */}
            </div>

            {/* Section 1: Toggles */}
            <div className="p-4 space-y-4 border-b border-border">
                <h3 className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-2">Sources</h3>

                {/* Toggle Item */}
                <div className="flex items-center justify-between group">
                    <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-blue-500" />
                        <span className="text-sm text-foreground">LLM Knowledge</span>
                    </div>
                    <button
                        onClick={() => setContextFlags(prev => ({ ...prev, useLLMData: !prev.useLLMData }))}
                        className={`w-10 h-5 rounded-full relative transition-colors ${contextFlags.useLLMData ? 'bg-primary' : 'bg-muted'}`}
                    >
                        <div className={`w-3 h-3 bg-background rounded-full absolute top-1 transition-transform ${contextFlags.useLLMData ? 'left-6' : 'left-1'}`} />
                    </button>
                </div>
                <p className="text-xs text-muted-foreground">
                    {contextFlags.useLLMData ? "Model uses internal training data." : "Model restricted to provided context only."}
                </p>

                {/* Toggle Item */}
                <div className="flex items-center justify-between group">
                    <div className="flex items-center gap-2">
                        <Database size={16} className="text-green-500" />
                        <span className="text-sm text-foreground">Documents (RAG)</span>
                    </div>
                    <button
                        onClick={() => setContextFlags(prev => ({ ...prev, useDocuments: !prev.useDocuments }))}
                        className={`w-10 h-5 rounded-full relative transition-colors ${contextFlags.useDocuments ? 'bg-primary' : 'bg-muted'}`}
                    >
                        <div className={`w-3 h-3 bg-background rounded-full absolute top-1 transition-transform ${contextFlags.useDocuments ? 'left-6' : 'left-1'}`} />
                    </button>
                </div>

                {/* Documents List (New) */}
                {attachments && attachments.length > 0 && (
                    <div className="mt-2 pl-6 space-y-1">
                        {attachments.map(att => (
                            <div key={att.id} className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 p-1.5 rounded border border-border/50">
                                <FileText size={12} />
                                <span className="truncate">{att.file_name}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Toggle Item */}
                <div className="flex items-center justify-between group">
                    <div className="flex items-center gap-2">
                        <Globe size={16} className="text-purple-500" />
                        <span className="text-sm text-foreground">Web Search</span>
                    </div>
                    <button
                        onClick={() => setContextFlags(prev => ({ ...prev, useWebSearch: !prev.useWebSearch }))}
                        className={`w-10 h-5 rounded-full relative transition-colors ${contextFlags.useWebSearch ? 'bg-primary' : 'bg-muted'}`}
                    >
                        <div className={`w-3 h-3 bg-background rounded-full absolute top-1 transition-transform ${contextFlags.useWebSearch ? 'left-6' : 'left-1'}`} />
                    </button>
                </div>
            </div>

            {/* Section 2: Context Search */}
            <div className="flex-1 overflow-hidden flex flex-col p-4">
                <h3 className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-2">Context Explorer</h3>

                {/* Search Box */}
                <div className="flex gap-2 mb-4">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        placeholder="Search vector DB..."
                        className="flex-1 bg-muted border-none text-sm p-2 rounded text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                        onClick={handleSearch}
                        disabled={isSearching}
                        className="bg-muted p-2 rounded text-muted-foreground hover:text-foreground hover:bg-muted/80 disabled:opacity-50"
                    >
                        <Search size={18} />
                    </button>
                </div>

                {/* Results List */}
                <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar">
                    {searchResults.length === 0 && !isSearching && (
                        <div className="text-center text-muted-foreground text-xs mt-10">
                            No results found. Try searching for keywords.
                        </div>
                    )}

                    {searchResults.map((result, idx) => (
                        <div key={idx} className="bg-muted/50 p-3 rounded-md border border-border hover:border-primary/50 transition-colors group cursor-pointer" onClick={() => setSelectedContext(result)}>
                            <div className="flex justify-between items-start mb-1">
                                <span className="text-sm font-bold text-foreground truncate pr-2">
                                    {result.meta?.filename || 'Unknown Document'}
                                </span>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {/* Score or ID? */}
                                </span>
                            </div>
                            <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                                {result.text}
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Modal for Full Text */}
            {selectedContext && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-card w-full max-w-2xl max-h-[80vh] rounded-lg border border-border shadow-2xl flex flex-col">
                        <div className="p-4 border-b border-border flex justify-between items-center">
                            <h3 className="font-bold text-foreground flex items-center gap-2">
                                <FileText size={18} className="text-primary" />
                                {selectedContext.meta?.filename || 'Context Detail'}
                            </h3>
                            <button onClick={() => setSelectedContext(null)} className="text-muted-foreground hover:text-destructive">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto text-foreground text-sm whitespace-pre-wrap font-mono leading-relaxed">
                            {selectedContext.text}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RightSidebar;
