# Glovy AI Agent Backend

Glovy is a witty and smart AI agent designed to facilitate real-time conversations between two people. Glovy analyzes message tone, detects when intervention is needed, and provides natural, contextual responses to enhance the conversation.

## Features

- **Real-time Message Processing**: Listens to Supabase real-time events for new messages
- **Tone Analysis**: Analyzes emotional tone and sentiment of messages using LLM
- **Smart Response Timing**: Decides when Glovy should interject based on conversation context
- **Context-Aware Responses**: Uses LangChain, Mem0, and RAG for intelligent response generation
- **Conversation Memory**: Maintains context across the conversation session
- **Supabase Integration**: Seamlessly integrates with existing Supabase schema

## Architecture

```
Frontend <-> Supabase <-> Backend (Glovy)
```

The backend subscribes to Supabase real-time changes on the `messages` table. When a new message is inserted, Glovy:
1. Analyzes the message tone
2. Determines if a response is needed
3. Generates a contextual response
4. Inserts the response back into Supabase

## Setup

### Prerequisites

- Python 3.8+
- Supabase project with the following tables:
  - `profiles`
  - `matches`
  - `messages`
- Google Gemini API key
- (Optional) Mem0 API key for enhanced memory

### Installation

1. Clone the repository and navigate to the backend directory:
```bash
cd PlanA-Backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file from `env.template`:
```bash
# Copy template
cp env.template .env

# Or use interactive setup
python setup_env.py
```

4. Configure your `.env` file with your credentials:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL=gemini-1.5-flash
MEM0_API_KEY=your_mem0_api_key  # Optional
```

## Running the Backend

### Using FastAPI (Recommended)

Start the FastAPI application:

```bash
# Using the run script
python run.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will:
- Start FastAPI server on http://0.0.0.0:8000
- Connect to Supabase
- Subscribe to real-time message events
- Process incoming messages and generate Glovy responses
- Provide API endpoints for health checks and webhooks

### API Endpoints

- `GET /api/v1/` - Root endpoint
- `GET /api/v1/health` - Health check
- `GET /api/v1/status` - Service status
- `POST /api/v1/webhook/message` - Webhook endpoint for Supabase
- `POST /api/v1/process-message` - Manually trigger message processing (testing)

Interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Supabase Schema

### Profiles Table
```sql
{
  "id": uuid,
  "full_name": text,
  "email": email,
  "partner": json  -- Information about the second person in the chat room
}
```

### Matches Table
```sql
{
  "id": uuid,
  "subject": text,
  "initiator_id": uuid,  -- References profiles.id
  "invitee_id": uuid,    -- References profiles.id
  "coach_persona": "glovy",
  "start_time": datetime,
  "end_time": datetime,
  "duration": int,  -- Session duration in minutes
  "metadata": json  -- Match onboarding info of 2 partners
}
```

### Messages Table
```sql
{
  "match_id": uuid,        -- References matches.id
  "sender_id": uuid,       -- References profiles.id (null for Glovy)
  "sender_role": text,     -- "A" (initiator), "B" (invitee), or "Glovy"
  "persona": text,
  "recipient_id": uuid,    -- For whispers, only visible to specific person
  "body": text,            -- Message content
  "message_type": text,    -- "text"
  "is_whisper": boolean,
  "created_at": timestamp  -- Auto-generated
}
```

## Frontend Integration

### Real-time Updates

The frontend should already be set up to listen to Supabase real-time changes. When Glovy inserts a message, it will automatically appear in the frontend through the existing Supabase real-time subscription.

### Message Format

Glovy's messages follow the same format as user messages:
- `sender_id`: `null` (Glovy has no profile)
- `sender_role`: `"Glovy"`
- `persona`: `"glovy"` (configurable)
- `body`: The generated response text
- `message_type`: `"text"`
- `is_whisper`: `false` (by default)

### Example Frontend Query

```javascript
// Supabase client query example
const { data, error } = await supabase
  .from('messages')
  .select('*')
  .eq('match_id', matchId)
  .order('created_at', { ascending: true })

// Real-time subscription
supabase
  .channel('messages')
  .on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'messages' },
    (payload) => {
      // Handle new message (including Glovy's messages)
      const newMessage = payload.new
      if (newMessage.sender_role === 'Glovy') {
        // Display Glovy's message
      }
    }
  )
  .subscribe()
```

## Configuration

### Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY`: (Optional) Service role key for admin operations
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `GOOGLE_MODEL`: Model to use (default: `gemini-1.5-flash`)
- `MEM0_API_KEY`: (Optional) Mem0 API key for enhanced memory
- `GLOVY_PERSONA`: Persona identifier (default: `"glovy"`)
- `GLOVY_RESPONSE_THRESHOLD`: Minimum tone intensity to respond (0.0-1.0, default: 0.7)
- `GLOVY_MIN_MESSAGES_BEFORE_RESPONSE`: Minimum messages before first response (default: 2)
- `ENVIRONMENT`: `development` or `production`

### Response Timing Logic

Glovy responds when:
- Tone analysis indicates a response is needed
- Minimum message count threshold is met
- Glovy hasn't responded too recently
- Tone intensity exceeds the threshold (or urgency is high)
- Specific intervention scenarios are detected (confusion, frustration, stagnation)

## Architecture Details

### Components

1. **SupabaseClient** (`supabase_client.py`): Handles all Supabase operations
2. **ToneAnalyzer** (`tone_analyzer.py`): Analyzes message tone and sentiment
3. **GlovyAgent** (`glovy_agent.py`): Core AI agent with LangChain, Mem0, and RAG
4. **ResponseTiming** (`response_timing.py`): Determines optimal response timing
5. **MessageProcessor** (`message_processor.py`): Main processing pipeline
6. **Main** (`main.py`): Entry point and real-time subscription handler

### Message Flow

1. User sends message → Frontend inserts into Supabase `messages` table
2. Supabase real-time triggers → Backend receives INSERT event
3. MessageProcessor analyzes message tone
4. ResponseTiming determines if Glovy should respond
5. GlovyAgent generates contextual response
6. Response inserted back into Supabase `messages` table
7. Frontend receives real-time update and displays Glovy's message

## Development

### Logging

Logging is configured based on the `ENVIRONMENT` variable:
- `development`: INFO level logging
- `production`: WARNING level logging

### Testing

To test the backend locally:

1. Ensure your Supabase project is running
2. Start the backend: `python main.py`
3. Send a test message from the frontend
4. Check logs for Glovy's processing and response

## Troubleshooting

### Glovy not responding

- Check that Supabase real-time is enabled for the `messages` table
- Verify environment variables are set correctly
- Check logs for errors in message processing
- Ensure Google Gemini API key is valid and has quota

### Memory issues

- Mem0 is optional; the backend works without it
- If Mem0 is configured but failing, check API key validity
- Memory errors are logged but don't stop message processing

### Real-time connection issues

- Verify Supabase URL and key are correct
- Check network connectivity
- Ensure Supabase real-time is enabled in your project settings

## License

[Your License Here]

