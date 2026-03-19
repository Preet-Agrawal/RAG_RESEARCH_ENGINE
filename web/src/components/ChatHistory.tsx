'use client';

import { MessageSquare, Trash2, FileText } from 'lucide-react';
import type { SavedChat } from '@/lib/chatStorage';

interface ChatHistoryProps {
  chats: SavedChat[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ChatHistory({ chats, activeChatId, onSelectChat, onDeleteChat }: ChatHistoryProps) {
  if (chats.length === 0) return null;

  return (
    <div className="border-t border-claude-border">
      <div className="px-3 py-2.5">
        <h3 className="text-xs font-semibold text-claude-text-muted uppercase tracking-wider">
          Recent Chats
        </h3>
      </div>
      <div className="px-2 pb-2 space-y-0.5">
        {chats.map((chat) => (
          <div
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            className={`group flex items-start gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-colors ${
              activeChatId === chat.id
                ? 'bg-claude-surface-hover'
                : 'hover:bg-claude-surface'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-claude-text-muted mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-claude-text-secondary truncate">
                {chat.title}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <FileText className="w-2.5 h-2.5 text-claude-text-muted" />
                <span className="text-[10px] text-claude-text-muted truncate">{chat.documentName}</span>
                <span className="text-[10px] text-claude-text-muted">&middot;</span>
                <span className="text-[10px] text-claude-text-muted">{timeAgo(chat.updatedAt)}</span>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteChat(chat.id);
              }}
              className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-claude-surface-hover text-claude-text-muted hover:text-red-400 transition-all flex-shrink-0"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
