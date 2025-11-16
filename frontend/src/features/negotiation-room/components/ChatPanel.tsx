'use client';

import { useEffect, useRef } from 'react';
import { useNegotiation } from '@/store/negotiationStore';
import { Card } from '@/components/Card';
import type { Message } from '@/lib/types';
import { formatTimestamp, highlightMentions, stripThinking } from '@/utils/formatters';
import { getSellerColor } from '@/lib/constants';

interface ChatPanelProps {
  roomId: string;
}

function BuyerMessage({ message }: { message: Message }) {
  const displayMessage = stripThinking(message.message);
  
  return (
    <div className="flex justify-start mb-4 animate-slide-in">
      <div className="max-w-[80%]">
        <div className="flex items-center space-x-2 mb-1">
          <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white text-sm font-bold">
            B
          </div>
          <span className="text-sm font-medium text-neutral-700">{message.sender_name}</span>
          <span className="text-xs text-neutral-500">{formatTimestamp(message.timestamp)}</span>
        </div>
        <div className="bg-primary-100 text-primary-900 rounded-lg rounded-tl-none px-4 py-2">
          {displayMessage}
        </div>
      </div>
    </div>
  );
}

function SellerMessage({ message, sellerIndex }: { message: Message; sellerIndex: number }) {
  const sellerColor = getSellerColor(sellerIndex);
  const displayMessage = stripThinking(message.message);
  
  return (
    <div className="flex justify-end mb-4 animate-slide-in">
      <div className="max-w-[80%]">
        <div className="flex items-center justify-end space-x-2 mb-1">
          <span className="text-xs text-neutral-500">{formatTimestamp(message.timestamp)}</span>
          <span className="text-sm font-medium text-neutral-700">{message.sender_name}</span>
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
            style={{ backgroundColor: sellerColor }}
          >
            S
          </div>
        </div>
        <div className="bg-neutral-100 text-neutral-900 rounded-lg rounded-tr-none px-4 py-2">
          <div dangerouslySetInnerHTML={{ __html: highlightMentions(displayMessage) }} />
          {message.updated_offer && (
            <div className="mt-2 pt-2 border-t border-neutral-300">
              <p className="text-sm font-semibold text-secondary-600">
                💰 Offer: ${message.updated_offer.price}/unit (x{message.updated_offer.quantity})
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SystemMessage({ message }: { message: Message }) {
  return (
    <div className="flex justify-center mb-4">
      <div className="bg-neutral-200 text-neutral-700 rounded-full px-4 py-1 text-sm">
        {message.message}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-neutral-100 rounded-lg px-4 py-3">
        <div className="flex space-x-2">
          <div className="w-2 h-2 bg-neutral-400 rounded-full animate-typing" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-neutral-400 rounded-full animate-typing" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-neutral-400 rounded-full animate-typing" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

export function ChatPanel({ roomId }: ChatPanelProps) {
  const { rooms } = useNegotiation();
  const negotiationState = rooms[roomId];
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [negotiationState?.messages]);

  const getSellerIndex = (senderId?: string) => {
    if (!senderId) return 0;
    // This is a simple hash to get consistent colors
    return Math.abs(senderId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 10;
  };

  return (
    <Card
      header={
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Live Chat</h2>
            <p className="text-sm text-neutral-600">Negotiation in progress</p>
          </div>
          {negotiationState?.isStreaming && (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-secondary-500 rounded-full animate-pulse" />
              <span className="text-sm text-secondary-600 font-medium">Streaming</span>
            </div>
          )}
        </div>
      }
    >
      <div className="h-[600px] overflow-y-auto pr-2">
        {!negotiationState?.messages || negotiationState.messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-neutral-500">
            <svg className="w-16 h-16 mb-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm font-medium mb-1">Negotiation Starting...</p>
            <p className="text-xs">The buyer is crafting an opening message</p>
          </div>
        ) : (
          <div>
            {negotiationState.messages.map((message, index) => {
              const senderType = message.sender_type?.toLowerCase().trim();
              
              if (senderType === 'buyer') {
                return <BuyerMessage key={message.message_id || index} message={message} />;
              } else if (senderType === 'seller') {
                return (
                  <SellerMessage
                    key={message.message_id || index}
                    message={message}
                    sellerIndex={getSellerIndex(message.sender_id)}
                  />
                );
              } else {
                return <SystemMessage key={message.message_id || index} message={message} />;
              }
            })}
            
            {negotiationState.isStreaming && <TypingIndicator />}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </Card>
  );
}

