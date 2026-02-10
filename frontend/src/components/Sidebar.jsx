import { Plus, MessageSquare, Search, Menu, X, Tag } from 'lucide-react';
import { cn } from '../lib/utils';

export default function Sidebar({ isOpen, chats, activeChat, onNewChat, onSelectChat, onToggle, backendOnline }) {
    return (
        <div
            className={cn(
                "bg-card border-r border-border flex flex-col transition-all duration-300 ease-in-out relative",
                isOpen ? "w-80" : "w-0 opacity-0 overflow-hidden"
            )}
        >
            <div className="p-4 border-b border-border flex items-center justify-between">
                <h2 className="font-semibold text-lg">Chats</h2>
                <button onClick={onToggle} className="lg:hidden p-2 hover:bg-accent rounded-md">
                    <X size={20} />
                </button>
            </div>

            <div className="p-4">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-2 px-4 rounded-md hover:bg-primary/90 transition shadow-sm"
                >
                    <Plus size={20} />
                    <span>New Chat</span>
                </button>
            </div>

            <div className="px-4 pb-2">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search chats..."
                        className="w-full pl-9 pr-4 py-2 bg-muted/50 border-none rounded-md text-sm focus:ring-1 focus:ring-primary outline-none"
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                {chats.length === 0 && (
                    <p className="text-center text-sm text-muted-foreground mt-10">No chats yet.</p>
                )}
                {chats.map((chat) => (
                    <button
                        key={chat.id}
                        onClick={() => onSelectChat(chat)}
                        className={cn(
                            "w-full text-left px-3 py-3 rounded-lg flex items-start gap-3 transition group hover:bg-accent",
                            activeChat?.id === chat.id ? "bg-accent" : ""
                        )}
                    >
                        <MessageSquare size={18} className="mt-1 text-muted-foreground group-hover:text-foreground" />
                        <div className="flex-1 min-w-0">
                            <p className={cn("text-sm font-medium truncate", activeChat?.id === chat.id ? "text-foreground" : "text-muted-foreground group-hover:text-foreground")}>
                                {chat.title}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {new Date(chat.updated_at).toLocaleDateString()}
                            </p>
                        </div>
                    </button>
                ))}
            </div>

            {/* Bottom User/Settings Area */}
            <div className="p-4 border-t border-border space-y-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className={cn("w-2 h-2 rounded-full", backendOnline ? "bg-green-500" : "bg-red-500")}></div>
                    <span>{backendOnline ? "Local System Online" : "Local System Offline"}</span>
                </div>
            </div>
        </div>
    );
}
