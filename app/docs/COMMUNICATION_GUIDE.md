# Frontend ↔ Backend ↔ Supabase Communication Guide

This guide explains how the three components communicate in the Glovy system.

## Architecture Overview

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │ ◄─────► │   Supabase  │ ◄─────► │   Backend   │
│  (React/    │         │  (Database) │         │  (FastAPI)  │
│   Next.js)  │         │             │         │   (Glovy)   │
└─────────────┘         └─────────────┘         └─────────────┘
```

## Communication Flow

### 1. User Sends Message (Frontend → Supabase)

**Frontend Code:**
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// User sends a message
async function sendMessage(matchId, userId, messageText, senderRole) {
  const { data, error } = await supabase
    .from('messages')
    .insert({
      match_id: matchId,
      sender_id: userId,
      sender_role: senderRole, // 'A' or 'B'
      body: messageText,
      message_type: 'text',
      is_whisper: false
    })
    .select()
    .single()

  if (error) {
    console.error('Error sending message:', error)
    return null
  }

  return data
}
```

### 2. Supabase Triggers Real-time Event (Supabase → Backend)

**Automatic:** When a message is inserted into Supabase:
- Supabase sends a real-time event
- Backend is already subscribed and receives it automatically
- **No frontend action needed!**

### 3. Backend Processes Message (Backend Internal)

The backend automatically:
1. Receives the real-time event
2. Analyzes message tone
3. Determines if Glovy should respond
4. Generates Glovy's response
5. Inserts Glovy's message back into Supabase

**No frontend action needed!**

### 4. Frontend Receives Glovy's Response (Supabase → Frontend)

**Frontend Code:**
```javascript
// Set up real-time subscription for a match
function subscribeToMessages(matchId, onNewMessage) {
  const channel = supabase
    .channel(`match:${matchId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'messages',
        filter: `match_id=eq.${matchId}`
      },
      (payload) => {
        const newMessage = payload.new
        
        // Check if it's from Glovy
        if (newMessage.sender_role === 'Glovy') {
          console.log('Glovy responded:', newMessage.body)
          onNewMessage(newMessage)
        } else {
          // Regular user message
          onNewMessage(newMessage)
        }
      }
    )
    .subscribe()

  return channel
}

// Usage in React component
useEffect(() => {
  const channel = subscribeToMessages(matchId, (message) => {
    // Update your messages state
    setMessages(prev => [...prev, message])
  })

  // Cleanup on unmount
  return () => {
    supabase.removeChannel(channel)
  }
}, [matchId])
```

## Complete Frontend Integration Example

### React/Next.js Component

```javascript
'use client'
import { useState, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

export default function ChatRoom({ matchId, userId, senderRole }) {
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(false)

  // Load initial messages
  useEffect(() => {
    loadMessages()
  }, [matchId])

  // Set up real-time subscription
  useEffect(() => {
    const channel = supabase
      .channel(`match:${matchId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `match_id=eq.${matchId}`
        },
        (payload) => {
          const message = payload.new
          setMessages(prev => {
            // Avoid duplicates
            if (prev.find(m => m.id === message.id)) {
              return prev
            }
            return [...prev, message]
          })
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [matchId])

  async function loadMessages() {
    const { data, error } = await supabase
      .from('messages')
      .select('*')
      .eq('match_id', matchId)
      .order('created_at', { ascending: true })

    if (error) {
      console.error('Error loading messages:', error)
      return
    }

    setMessages(data || [])
  }

  async function handleSendMessage(e) {
    e.preventDefault()
    if (!newMessage.trim()) return

    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('messages')
        .insert({
          match_id: matchId,
          sender_id: userId,
          sender_role: senderRole,
          body: newMessage,
          message_type: 'text',
          is_whisper: false
        })
        .select()
        .single()

      if (error) throw error

      // Message will appear via real-time subscription
      // But we can optimistically add it
      setMessages(prev => [...prev, data])
      setNewMessage('')
    } catch (error) {
      console.error('Error sending message:', error)
      alert('Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-room">
      <div className="messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${
              message.sender_role === 'Glovy' ? 'glovy-message' : 'user-message'
            }`}
          >
            {message.sender_role === 'Glovy' && (
              <span className="glovy-badge">Glovy</span>
            )}
            <p>{message.body}</p>
            <span className="timestamp">
              {new Date(message.created_at).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSendMessage}>
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          Send
        </button>
      </form>
    </div>
  )
}
```

## Backend API Endpoints

### Health Check
```javascript
// Frontend can check if backend is running
async function checkBackendHealth() {
  const response = await fetch('http://localhost:8000/api/v1/health')
  const data = await response.json()
  console.log('Backend status:', data)
  // { status: "healthy", supabase_connected: true, ... }
}
```

### Manual Message Processing (Testing Only)
```javascript
// Only use for testing - real-time subscription handles this automatically
async function triggerProcessing(message) {
  const response = await fetch('http://localhost:8000/api/v1/process-message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message)
  })
  return await response.json()
}
```

## Supabase Configuration

### 1. Enable Real-time for Messages Table

In Supabase Dashboard:
1. Go to **Database** → **Replication**
2. Find the `messages` table
3. Toggle **Enable Realtime** to ON

Or use SQL:
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
```

### 2. Row Level Security (RLS)

Ensure your RLS policies allow:
- Users to insert their own messages
- Users to read messages in their matches
- Backend service role to insert Glovy messages

Example policies:
```sql
-- Allow users to insert their own messages
CREATE POLICY "Users can insert own messages"
ON messages FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = sender_id);

-- Allow users to read messages in their matches
CREATE POLICY "Users can read match messages"
ON messages FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM matches
    WHERE matches.id = messages.match_id
    AND (matches.initiator_id = auth.uid() OR matches.invitee_id = auth.uid())
  )
);

-- Allow service role to insert Glovy messages
CREATE POLICY "Service role can insert Glovy messages"
ON messages FOR INSERT
TO service_role
WITH CHECK (sender_role = 'Glovy');
```

## Environment Variables

### Frontend (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Optional, for health checks
```

### Backend (.env)
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # For inserting Glovy messages
GOOGLE_API_KEY=your-google-api-key
ENVIRONMENT=development
```

## Message Flow Diagram

```
1. User types message in frontend
   ↓
2. Frontend → Supabase: INSERT message
   ↓
3. Supabase → Backend: Real-time event (automatic)
   ↓
4. Backend processes message
   - Analyzes tone
   - Generates Glovy response
   - Inserts Glovy message into Supabase
   ↓
5. Supabase → Frontend: Real-time event (automatic)
   ↓
6. Frontend displays Glovy's message
```

## Key Points

1. **Frontend only talks to Supabase** - No direct API calls to backend needed for normal operation
2. **Backend listens automatically** - Real-time subscription handles everything
3. **Glovy responses appear automatically** - Frontend real-time subscription receives them
4. **No polling needed** - Everything is real-time via Supabase
5. **Backend API is optional** - Only needed for health checks or manual testing

## Troubleshooting

### Messages not appearing?
- Check Supabase real-time is enabled for `messages` table
- Verify RLS policies allow reading messages
- Check browser console for subscription errors

### Glovy not responding?
- Check backend logs: `uvicorn app.main:app --reload`
- Verify backend is subscribed: Check `/api/v1/status` endpoint
- Check Supabase real-time is enabled

### CORS errors?
- Backend CORS is configured to allow all origins in development
- For production, update `app/main.py` CORS settings

## Testing the Flow

1. **Start Backend:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Check Backend Status:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **Send Test Message from Frontend:**
   ```javascript
   await supabase.from('messages').insert({
     match_id: 'test-match-id',
     sender_id: 'test-user-id',
     sender_role: 'A',
     body: 'Hello, this is a test message!'
   })
   ```

4. **Watch Backend Logs:**
   - Should see: "New message received: ..."
   - Should see: "Glovy response inserted for match ..."

5. **Check Frontend:**
   - Real-time subscription should receive Glovy's response
   - Message should appear in chat

