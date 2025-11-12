# Frontend and Supabase Integration Guide

This document explains how the Glovy backend integrates with your existing frontend and Supabase setup.

## Architecture Overview

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│ Frontend │ ◄─────► │ Supabase │ ◄─────► │ Backend  │
│          │         │          │         │ (Glovy)  │
└──────────┘         └──────────┘         └──────────┘
```

## Message Flow

### 1. User Sends Message (Frontend → Supabase)

When a user sends a message from the frontend:

```javascript
// Frontend code example
const { data, error } = await supabase
  .from('messages')
  .insert({
    match_id: matchId,
    sender_id: userId,
    sender_role: 'A', // or 'B'
    body: messageText,
    message_type: 'text',
    is_whisper: false
  });
```

### 2. Supabase Real-time Trigger (Supabase → Backend)

Supabase automatically triggers a real-time event when a new message is inserted. The backend is subscribed to these events:

- **Event Type**: `INSERT`
- **Table**: `messages`
- **Schema**: `public`

The backend receives the new message payload and processes it.

### 3. Glovy Processes Message (Backend)

The backend:
1. Analyzes the message tone
2. Determines if Glovy should respond
3. Generates a contextual response
4. Inserts Glovy's response back into Supabase

### 4. Frontend Receives Glovy's Response (Supabase → Frontend)

Your existing frontend real-time subscription will automatically receive Glovy's message:

```javascript
// Frontend real-time subscription (should already exist)
supabase
  .channel('messages')
  .on('postgres_changes', 
    { 
      event: 'INSERT', 
      schema: 'public', 
      table: 'messages',
      filter: `match_id=eq.${matchId}`
    },
    (payload) => {
      const newMessage = payload.new;
      
      // Check if it's from Glovy
      if (newMessage.sender_role === 'Glovy') {
        // Display Glovy's message in the chat
        displayMessage(newMessage);
      }
    }
  )
  .subscribe();
```

## Supabase Configuration

### Required Supabase Settings

1. **Enable Real-time** for the `messages` table:
   - Go to Supabase Dashboard → Database → Replication
   - Enable replication for the `messages` table
   - Or use SQL:
   ```sql
   ALTER PUBLICATION supabase_realtime ADD TABLE messages;
   ```

2. **Row Level Security (RLS)**:
   - Ensure your RLS policies allow:
     - Users to insert their own messages
     - Users to read messages in their matches
     - The backend service role to insert Glovy messages

   Example RLS policy for backend:
   ```sql
   -- Allow service role to insert Glovy messages
   CREATE POLICY "Allow service role to insert Glovy messages"
   ON messages
   FOR INSERT
   TO service_role
   WITH CHECK (sender_role = 'Glovy');
   ```

### Database Schema Requirements

Ensure your Supabase schema matches the expected structure:

#### Messages Table
```sql
CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
  sender_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  sender_role TEXT NOT NULL, -- 'A', 'B', or 'Glovy'
  persona TEXT,
  recipient_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  body TEXT NOT NULL,
  message_type TEXT DEFAULT 'text',
  is_whisper BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for performance
CREATE INDEX idx_messages_match_id ON messages(match_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

## Frontend Integration Points

### 1. Message Display

Your frontend should handle Glovy messages the same way as user messages, but with special styling:

```javascript
function renderMessage(message) {
  const isGlovy = message.sender_role === 'Glovy';
  
  return (
    <div className={`message ${isGlovy ? 'glovy-message' : 'user-message'}`}>
      {isGlovy && <span className="glovy-badge">Glovy</span>}
      <p>{message.body}</p>
      <span className="timestamp">{formatTime(message.created_at)}</span>
    </div>
  );
}
```

### 2. Real-time Subscription

Ensure your frontend subscribes to message updates:

```javascript
// Subscribe to messages for a specific match
const channel = supabase
  .channel(`match:${matchId}`)
  .on('postgres_changes', 
    { 
      event: '*', // Listen to INSERT, UPDATE, DELETE
      schema: 'public', 
      table: 'messages',
      filter: `match_id=eq.${matchId}`
    },
    (payload) => {
      handleMessageChange(payload);
    }
  )
  .subscribe();

// Cleanup on unmount
return () => {
  supabase.removeChannel(channel);
};
```

### 3. Message Filtering

You may want to filter or highlight Glovy messages:

```javascript
// Get all messages including Glovy's
const { data: messages } = await supabase
  .from('messages')
  .select('*')
  .eq('match_id', matchId)
  .order('created_at', { ascending: true });

// Separate user and Glovy messages if needed
const userMessages = messages.filter(m => m.sender_role !== 'Glovy');
const glovyMessages = messages.filter(m => m.sender_role === 'Glovy');
```

## Backend Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Optional, for admin operations

# Google Gemini
GOOGLE_API_KEY=sk-...
GOOGLE_MODEL=gemini-1.5-flash

# Mem0 (Optional)
MEM0_API_KEY=your-mem0-key

# Glovy Settings
GLOVY_PERSONA=glovy
GLOVY_RESPONSE_THRESHOLD=0.7
GLOVY_MIN_MESSAGES_BEFORE_RESPONSE=2

# Environment
ENVIRONMENT=development
```

### Starting the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
python main.py
```

The backend will:
- Connect to Supabase
- Subscribe to real-time message events
- Process messages and generate Glovy responses
- Log all activities

## Testing the Integration

### 1. Test Message Flow

1. Send a message from the frontend
2. Check backend logs to see if the message was received
3. Wait for Glovy's response (if conditions are met)
4. Verify Glovy's message appears in the frontend

### 2. Test Real-time Updates

1. Open the chat in two browser windows
2. Send a message from one window
3. Verify it appears in both windows
4. Verify Glovy's response appears in both windows

### 3. Test Glovy Response Conditions

Glovy responds when:
- Tone analysis indicates a response is needed
- Minimum message threshold is met
- Tone intensity exceeds threshold
- Specific intervention scenarios are detected

To test, try sending messages with:
- Confusion or questions
- Negative sentiment
- Frustration
- Conversation stagnation

## Troubleshooting

### Glovy Not Responding

1. **Check Backend Logs**:
   ```bash
   # Look for processing messages
   tail -f logs/glovy.log  # if logging to file
   ```

2. **Verify Real-time Subscription**:
   - Check Supabase Dashboard → Database → Replication
   - Ensure `messages` table has real-time enabled

3. **Check Message Format**:
   - Verify `sender_role` is not "Glovy" (Glovy ignores its own messages)
   - Verify `match_id` is valid

4. **Check Tone Analysis**:
   - Glovy may not respond if tone doesn't meet threshold
   - Adjust `GLOVY_RESPONSE_THRESHOLD` in `.env` if needed

### Messages Not Appearing in Frontend

1. **Check Real-time Subscription**:
   - Verify frontend is subscribed to the correct channel
   - Check Supabase connection status

2. **Check RLS Policies**:
   - Ensure users can read messages in their matches
   - Verify Glovy messages are readable

3. **Check Message Format**:
   - Verify `match_id` matches the frontend's match
   - Check `sender_role` is "Glovy"

### Backend Connection Issues

1. **Verify Supabase Credentials**:
   - Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
   - Test connection with Supabase client

2. **Check Network**:
   - Ensure backend can reach Supabase
   - Check firewall settings

3. **Verify Real-time Support**:
   - Supabase real-time requires WebSocket support
   - Check if your network allows WebSocket connections

## Security Considerations

1. **API Keys**: Never commit `.env` file to version control
2. **Service Role Key**: Use service role key only in backend, never in frontend
3. **RLS Policies**: Ensure proper RLS policies are in place
4. **Rate Limiting**: Consider implementing rate limiting for Glovy responses
5. **Input Validation**: Backend validates all inputs before processing

## Performance Optimization

1. **Response Caching**: Consider caching common responses
2. **Batch Processing**: Process multiple messages if needed
3. **Database Indexing**: Ensure proper indexes on `match_id` and `created_at`
4. **Connection Pooling**: Supabase client handles connection pooling automatically

## Monitoring

Monitor the following:
- Backend logs for errors
- Supabase real-time connection status
- Response generation time
- Message processing rate
- Error rates

## Support

For issues or questions:
1. Check backend logs
2. Verify Supabase configuration
3. Test with simple messages first
4. Review this integration guide

