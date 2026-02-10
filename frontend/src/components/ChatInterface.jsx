import React, { useState, useEffect, useRef } from 'react';
import { Send, Paperclip, Loader2, Cpu, FileText, Plus, MoreVertical } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { getChat, getModels, uploadFile, getStreamUrl, updateChat } from '../services/api';
import { cn } from '../lib/utils';
import { fetchEventSource } from '@microsoft/fetch-event-source';

const parseContent = (content) => {
    let thought = null;
    let response = content;

    // Pattern 1: <think> tags (DeepSeek style)
    const thinkStart = "<think>";
    const thinkEnd = "</think>";

    if (content.includes(thinkStart)) {
        const startIndex = content.indexOf(thinkStart) + thinkStart.length;
        const endIndex = content.indexOf(thinkEnd);

        if (endIndex !== -1) {
            thought = content.substring(startIndex, endIndex).trim();
            response = content.substring(endIndex + thinkEnd.length).trim();
        } else {
            thought = content.substring(startIndex).trim();
            response = null; // Still thinking
        }
        return { thought, response };
    }

    // Pattern 2: "Thinking..." text (Custom style)
    const textStart = "Thinking...";
    const textEnd = "...done thinking";

    if (content.startsWith(textStart)) {
        const endIndex = content.indexOf(textEnd);
        if (endIndex !== -1) {
            thought = content.substring(textStart.length, endIndex).trim();
            response = content.substring(endIndex + textEnd.length).trim();
        } else {
            thought = content.substring(textStart.length).trim();
            response = null;
        }
        return { thought, response };
    }

    return { thought, response };
};

export default function ChatInterface({ chat, onChatUpdate, contextFlags, toggleRightSidebar, overwriteMode }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [models, setModels] = useState([]);
    // Initialize model from localStorage
    const [selectedModel, setSelectedModel] = useState(() => localStorage.getItem('selectedModel') || "");
    const [isLoading, setIsLoading] = useState(false);
    const [attachments, setAttachments] = useState([]);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);

    const [viewPrompt, setViewPrompt] = useState(null);


    useEffect(() => {
        if (selectedModel) {
            localStorage.setItem('selectedModel', selectedModel);
        }
    }, [selectedModel]);

    useEffect(() => {
        loadChatData();
        fetchModels();
    }, [chat.id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const loadChatData = async () => {
        try {
            const data = await getChat(chat.id);
            setMessages(data.messages || []);
            setAttachments([]); // Reset attachments for new message
        } catch (error) {
            console.error("Error loading chat", error);
        }
    };

    const fetchModels = async () => {
        try {
            const data = await getModels();
            setModels(data);
            if (data.length > 0) {
                // If current selection is invalid or empty, pick the first one
                // But if we have a valid one from localStorage (set in state init), keep it if it exists in data
                const currentExists = data.some(m => m.name === selectedModel);

                if (!selectedModel || !currentExists) {
                    setSelectedModel(data[0].name);
                }
            }
        } catch (error) {
            console.error("Error loading models", error);
            // Fallback
            setModels([{ name: "llama3" }, { name: "mistral" }]);
        }
    };

    const [abortController, setAbortController] = useState(null);

    const handleStopGeneration = () => {
        if (abortController) {
            abortController.abort();
            setAbortController(null);
            setIsLoading(false);
            setMessages(prev => {
                // Append [Stopped] to current streaming message
                const newMsgs = [...prev];
                const lastMsg = newMsgs[newMsgs.length - 1];
                if (lastMsg.isStreaming) {
                    lastMsg.isStreaming = false;
                    lastMsg.content += " [Stopped]";
                }
                return newMsgs;
            });
        }
    };

    const handleSendMessage = async () => {
        if ((!input.trim() && attachments.length === 0) || isLoading) return;

        // 1. Capture and Clear Inputs Immediately
        const currentInput = input;
        const currentAttachments = [...attachments];

        setInput("");
        setAttachments([]); // Clear immediately from input area
        setIsLoading(true);

        const userMessage = {
            role: 'user',
            content: currentInput,
            created_at: new Date().toISOString(),
            attachments: currentAttachments // Add for local display
        };

        // 2. Add User Message to Chat
        setMessages(prev => [...prev, userMessage]);

        // 3. Add Assistant Placeholder (with Status)
        setMessages(prev => [...prev, {
            role: 'assistant',
            model_used: selectedModel,
            content: currentAttachments.length > 0 ? "Processing the File..." : "",
            created_at: new Date().toISOString(),
            isStreaming: true
        }]);

        const controller = new AbortController();
        setAbortController(controller);

        let finalAttachmentIds = [];

        try {
            // 4. Process Attachments (Upload)
            if (currentAttachments.length > 0) {
                const uploadResults = await Promise.all(
                    currentAttachments.map(async (att) => {
                        if (att.isPending) {
                            const uploaded = await uploadFile(att.file, overwriteMode);
                            return uploaded.id;
                        }
                        return att.id;
                    })
                );
                finalAttachmentIds = uploadResults;

                // 5. Update Status: File Processed
                setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    if (lastMsg.role === 'assistant' && lastMsg.isStreaming) {
                        lastMsg.content = "File Processed. Generating Text...";
                    }
                    return newMsgs;
                });
            }
        } catch (error) {
            console.error("Error uploading files", error);
            setIsLoading(false);
            setAbortController(null);
            setMessages(prev => {
                const newMsgs = [...prev];
                // Replace the placeholder with error
                const lastMsg = newMsgs[newMsgs.length - 1];
                const errorDetail = error.response?.data?.detail || error.message;
                lastMsg.content = `**Error:** Failed to process attachments: ${errorDetail}`;
                lastMsg.isStreaming = false;
                return newMsgs;
            });
            return;
        }

        // 6. Start Streaming Response
        try {
            let fullResponse = "";
            let isFirstChunk = true;

            await fetchEventSource(getStreamUrl(), {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chat.id,
                    content: userMessage.content,
                    model_used: selectedModel,
                    attachments: finalAttachmentIds,
                    // Use prop or default
                    use_llm_data: contextFlags?.useLLMData ?? true,
                    use_documents: contextFlags?.useDocuments ?? true,
                    use_web_search: contextFlags?.useWebSearch ?? false
                }),
                signal: controller.signal,
                openWhenHidden: true, // Prevent auto-retry behavior on tab switch
                onopen(response) {
                    if (response.ok) {
                        return; // proceed
                    } else {
                        throw new Error(`Failed to send message: ${response.statusText}`);
                    }
                },
                onmessage(msg) {
                    if (msg.data === '[DONE]') {
                        // Stop the stream and retry loop manually
                        setIsLoading(false);
                        setAbortController(null);
                        onChatUpdate();
                        loadChatData();
                        controller.abort();
                        return;
                    }
                    const parsed = JSON.parse(msg.data);
                    if (parsed.error) {
                        fullResponse += `**Error:** ${parsed.error}`;
                        setMessages(prev => {
                            const newMsgs = [...prev];
                            const lastMsg = newMsgs[newMsgs.length - 1];
                            lastMsg.content = fullResponse;
                            return newMsgs;
                        });
                        throw new Error(parsed.error);
                    }
                    if (parsed.chunk !== undefined) {
                        if (isFirstChunk) {
                            // Clear the "File Processed..." or "Processing..." status text
                            // and start showing the real response
                            fullResponse = "";
                            isFirstChunk = false;
                        }
                        fullResponse += parsed.chunk;
                        setMessages(prev => {
                            const newMsgs = [...prev];
                            const lastMsg = newMsgs[newMsgs.length - 1];
                            if (lastMsg.isStreaming) {
                                lastMsg.content = fullResponse;
                            }
                            return newMsgs;
                        });
                    }
                },
                onclose() {
                    // This handles server-side close. 
                    // To prevent auto-retry by fetch-event-source, we must throw.
                    // However, we only get here if [DONE] wasn't handled (e.g. error or premature close).

                    setMessages(prev => {
                        const newMsgs = [...prev];
                        const lastMsg = newMsgs[newMsgs.length - 1];
                        lastMsg.isStreaming = false;
                        if (isFirstChunk && lastMsg.role === 'assistant') {
                            // Connection closed but no content received from LLM
                            lastMsg.content += " [No response generated]";
                        }
                        return newMsgs;
                    });

                    setIsLoading(false);
                    setAbortController(null);
                    onChatUpdate();
                    loadChatData();

                    // Throw to stop retry
                    throw new Error("STREAM_CLOSED_BY_SERVER");
                },
                onerror(err) {
                    if (err.name === 'AbortError' || err.message === 'STREAM_CLOSED_BY_SERVER') {
                        // Expected termination. Throwing prevents fetch-event-source from retrying.
                        throw err;
                    }
                    console.error("Stream error", err);
                    // Always throw to prevent retry
                    if (err.message.includes("Failed to send")) {
                        setIsLoading(false);
                        setAbortController(null);
                    }
                    throw err;
                }
            });
        } catch (error) {
            if (error.name !== 'AbortError' && error.message !== 'STREAM_CLOSED_BY_SERVER') {
                console.error("Error sending message", error);
                setIsLoading(false);
                setAbortController(null);
                setMessages(prev => {
                    // Append error to whatever we have
                    const newMsgs = [...prev];
                    const lastMsg = newMsgs[newMsgs.length - 1];
                    lastMsg.content += `\n\n**Error:** ${error.message}`;
                    lastMsg.isStreaming = false;
                    return newMsgs;
                });
            }
        }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Add to pending state without uploading immediately
        const tempAtt = {
            id: `temp-${Date.now()}`,
            file_name: file.name,
            file: file,
            isPending: true
        };
        setAttachments(prev => [...prev, tempAtt]);

        // Reset input so same file can be selected again if needed
        e.target.value = null;
    };



    return (
        <div className="flex flex-col h-full bg-background relative">
            {/* Top Bar - Updated with Right Sidebar Toggle */}
            <div className="h-16 border-b border-border flex items-center justify-between px-6 bg-card/50 backdrop-blur-sm z-10 sticky top-0">
                <div className="flex flex-col gap-1 flex-1 mr-4">
                    {/* ... (existing Title and Tags) ... */}
                    <input
                        type="text"
                        value={chat.title}
                        onChange={(e) => onChatUpdate({ ...chat, title: e.target.value })}
                        onBlur={() => updateChat(chat.id, { title: chat.title })}
                        className="font-semibold text-lg bg-transparent border-none outline-none focus:ring-1 focus:ring-primary/50 rounded px-1 -ml-1 w-full max-w-md truncate"
                    />
                    {/* Tags UI (simplified for brevity in replacement, assuming strictly kept or mostly untouched if targeting correctly) */}
                    <div className="flex items-center gap-2 flex-wrap">
                        {chat.tags && chat.tags.map(tag => (
                            <span key={tag.id} className="text-xs px-2 py-0.5 rounded-full bg-accent text-muted-foreground flex items-center gap-1 group">
                                {tag.name}
                                {/* ... tag delete button ... */}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Model Selector */}
                    <div className="relative">
                        <Cpu size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <select
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="pl-9 pr-4 py-1.5 bg-muted/50 border border-border rounded-md text-sm focus:ring-1 focus:ring-primary outline-none appearance-none cursor-pointer hover:bg-muted"
                        >
                            {models.map(m => (
                                <option key={m.name} value={m.name}>{m.name}</option>
                            ))}
                        </select>
                    </div>


                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth">
                {/* ... (empty state) ... */}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={cn(
                            "flex w-full group/msg", // Add group for hover effects
                            msg.role === 'user' ? "justify-end" : "justify-start"
                        )}
                    >
                        <div className={cn(
                            "max-w-[80%] rounded-2xl px-5 py-4 shadow-sm relative",
                            msg.role === 'user'
                                ? "bg-primary text-primary-foreground rounded-br-none"
                                : "bg-card border border-border rounded-tl-none"
                        )}>


                            {/* Message Content */}
                            {/* ... (existing content rendering) ... */}
                            {/* Message Content */}
                            {/* ... (existing content rendering) ... */}
                            {(() => {
                                const { thought, response } = msg.role === 'assistant' ? parseContent(msg.content) : { thought: null, response: msg.content };
                                return (
                                    <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                                        {thought && (
                                            <div className="mb-2 p-3 bg-muted/50 rounded-lg border border-border/50 text-xs text-muted-foreground italic animate-pulse-slow">
                                                <div className="flex items-center gap-2 mb-1 not-italic font-semibold opacity-70">
                                                    <Cpu size={12} /> Thinking Process
                                                </div>
                                                {thought}
                                            </div>
                                        )}
                                        {response && (
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                rehypePlugins={[rehypeRaw]}
                                                components={{
                                                    code({ node, inline, className, children, ...props }) {
                                                        const match = /language-(\w+)/.exec(className || '')
                                                        return !inline && match ? (
                                                            <SyntaxHighlighter
                                                                {...props}
                                                                style={vscDarkPlus}
                                                                language={match[1]}
                                                                PreTag="div"
                                                            >
                                                                {String(children).replace(/\n$/, '')}
                                                            </SyntaxHighlighter>
                                                        ) : (
                                                            <code {...props} className={className}>
                                                                {children}
                                                            </code>
                                                        )
                                                    }
                                                }}
                                            >
                                                {response}
                                            </ReactMarkdown>
                                        )}
                                        {!response && msg.isStreaming && !thought && (
                                            <div className="flex items-center gap-2 text-muted-foreground italic">
                                                <Loader2 size={16} className="animate-spin" /> Generating...
                                            </div>
                                        )}
                                    </div>
                                );
                            })()}

                            {/* Attachments */}
                            {msg.attachments && msg.attachments.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {msg.attachments.map((att, i) => (
                                        <div key={i} className="flex items-center gap-2 bg-background/20 px-3 py-1.5 rounded-md text-xs border border-white/20">
                                            <FileText size={14} />
                                            <span className="truncate max-w-[150px]">{att.file_name}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Metadata & Actions */}
                            <div className="mt-2 flex items-center justify-end gap-2 opacity-70 text-xs relative">
                                {msg.role === 'assistant' && <span>{msg.model_used || selectedModel}</span>}
                                <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>

                                {/* User Message Menu (Three Dots) - Direct Action */}
                                {msg.role === 'user' && (
                                    <div className="relative ml-2">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setViewPrompt(msg.augmented_content || "Prompt content not available.");
                                            }}
                                            className="p-1 hover:bg-black/20 rounded-full text-current opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
                                            title="Show Full Prompt"
                                        >
                                            <MoreVertical size={14} className="rotate-90" />
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area (Keep as is just pass through) */}
            <div className="p-4 border-t border-border bg-card">
                {/* Prepare Input Area */}
                {/* Attachments Preview */}
                {attachments.length > 0 && (
                    <div className="flex gap-2 mb-2 overflow-x-auto pb-2">
                        {attachments.map(file => (
                            <div key={file.id} className="flex items-center gap-2 bg-muted px-3 py-1.5 rounded-md text-xs border border-border">
                                <FileText size={14} />
                                <span className="truncate max-w-[150px]">{file.file_name}</span>
                                <button onClick={() => setAttachments(prev => prev.filter(a => a.id !== file.id))} className="text-muted-foreground hover:text-destructive">×</button>
                            </div>
                        ))}
                    </div>
                )}

                <div className="flex items-end gap-2 bg-muted/30 border border-border rounded-xl p-2 focus-within:ring-2 focus-within:ring-primary/20 transition-all shadow-sm">
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        onChange={handleFileUpload}
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="p-2 text-muted-foreground hover:text-primary hover:bg-accent rounded-lg transition"
                        title="Attach file"
                    >
                        <Paperclip size={20} />
                    </button>

                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSendMessage();
                            }
                        }}
                        placeholder="Message..."
                        className="flex-1 bg-transparent border-none outline-none resize-none max-h-32 py-2 text-sm"
                        rows={1}
                        style={{ minHeight: '40px' }}
                    />

                    <button
                        onClick={isLoading ? handleStopGeneration : handleSendMessage}
                        disabled={!isLoading && (!input.trim() && attachments.length === 0)}
                        className={cn(
                            "p-2 rounded-lg transition",
                            (!isLoading && !input.trim() && attachments.length === 0)
                                ? "bg-muted text-muted-foreground cursor-not-allowed"
                                : isLoading
                                    ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                    : "bg-primary text-primary-foreground hover:bg-primary/90"
                        )}
                        title={isLoading ? "Stop generating" : "Send message"}
                    >
                        {isLoading ? <span className="w-5 h-5 flex items-center justify-center font-bold">■</span> : <Send size={20} />}
                    </button>
                </div>
                <p className="text-center text-xs text-muted-foreground mt-2">
                    AI responses can be inaccurate. Local content is stored securely on your device.
                </p>
            </div>

            {/* Modal for Full Prompt */}
            {viewPrompt && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-background w-full max-w-3xl max-h-[80vh] rounded-lg border border-border shadow-2xl flex flex-col">
                        <div className="p-4 border-b border-border flex justify-between items-center bg-muted/30">
                            <h3 className="font-bold flex items-center gap-2">
                                <FileText size={18} className="text-primary" />
                                Full Prompt Content
                            </h3>
                            <button onClick={() => setViewPrompt(null)} className="text-muted-foreground hover:text-destructive">
                                <span className="text-lg font-bold">×</span>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto font-mono text-sm whitespace-pre-wrap leading-relaxed">
                            {viewPrompt}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
