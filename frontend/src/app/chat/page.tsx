'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { ai, type ChatMessage } from '@/utils/api';
import { useAuthStore } from '@/stores/useAuthStore';

// Pull a human-readable message out of an axios error, falling back gracefully.
function errorDetail(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    // The API wraps errors as { error: { detail } }; also tolerate a plain { detail }.
    const data = error.response?.data as
      | { detail?: unknown; error?: { detail?: unknown } }
      | undefined;
    const detail = data?.error?.detail ?? data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return fallback;
}

export default function ChatPage() {
  const { isAuthenticated } = useAuthStore();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the message list pinned to the newest content as it streams in.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  if (!isAuthenticated) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium leading-6 text-gray-900">Chat</h2>
          <p className="mt-2 text-sm text-gray-500">Please sign in to use chat.</p>
        </div>
      </div>
    );
  }

  const send = async () => {
    const content = input.trim();
    if (!content || streaming) return;

    const userMessage: ChatMessage = { role: 'user', content };
    // Snapshot the outgoing conversation (history + new user turn) for the request.
    const outgoing: ChatMessage[] = [...messages, userMessage];

    // Show the user turn plus an empty assistant bubble that will grow as deltas arrive.
    setMessages([...outgoing, { role: 'assistant', content: '' }]);
    setInput('');
    setStreaming(true);

    let sawDelta = false;

    // Append streamed text to the trailing assistant bubble.
    const appendDelta = (delta: string) => {
      sawDelta = true;
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === 'assistant') {
          next[next.length - 1] = { ...last, content: last.content + delta };
        }
        return next;
      });
    };

    // Drop the trailing (empty) assistant bubble on failure.
    const dropAssistant = () => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.content === '') {
          return prev.slice(0, -1);
        }
        return prev;
      });
    };

    try {
      await ai.streamChat(
        {
          messages: outgoing,
          conversation_id: conversationId,
        },
        {
          onDelta: appendDelta,
          onDone: (returnedConversationId) => {
            // A stream that produced nothing useful is treated as an error.
            if (!sawDelta) {
              dropAssistant();
              toast.error('No response from the assistant.');
            } else if (returnedConversationId !== null && conversationId === null) {
              // Remember the server-side conversation so follow-ups stay in context.
              setConversationId(returnedConversationId);
            }
            setStreaming(false);
          },
          onError: (message) => {
            dropAssistant();
            toast.error(message);
            setStreaming(false);
          },
        }
      );
    } catch (error) {
      dropAssistant();
      toast.error(errorDetail(error, 'Something went wrong while chatting.'));
      setStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter inserts a newline.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold leading-6 text-gray-900">Chat</h1>
        <p className="mt-2 text-sm text-gray-500">
          Talk to the AI assistant. When no API key is configured, a built-in mock
          provider answers so the demo works offline.
        </p>
      </div>

      <div className="bg-white shadow rounded-lg flex flex-col h-[70vh]">
        {/* Message list */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 sm:p-6 space-y-4">
          {messages.length === 0 ? (
            <p className="text-sm text-gray-400 text-center mt-8">
              Start the conversation by sending a message below.
            </p>
          ) : (
            messages.map((m, i) => {
              const isUser = m.role === 'user';
              const isPending = streaming && i === messages.length - 1 && m.content === '';
              return (
                <div
                  key={i}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                      isUser
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {isPending ? (
                      <span className="text-gray-500">thinking…</span>
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-gray-200 px-4 py-3 sm:px-6">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
              disabled={streaming}
              className="flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={streaming || !input.trim()}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
            >
              {streaming ? 'Sending…' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
