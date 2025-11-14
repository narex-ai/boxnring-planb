# Quick Start Guide

Get Glovy up and running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Supabase project with `profiles`, `matches`, and `messages` tables
- Google Gemini API key
- (Optional) Mem0 API key

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment

### Option A: Use Setup Script (Recommended)

```bash
python setup_env.py
```

This interactive script will guide you through setting up your `.env` file.

### Option B: Manual Setup

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
GOOGLE_API_KEY=sk-your-gemini-key
GOOGLE_MODEL=gemini-2.5-flash
ENVIRONMENT=development
```

## Step 3: Enable Supabase Real-time

In your Supabase Dashboard:

1. Go to **Database** → **Replication**
2. Find the `messages` table
3. Toggle **Enable** for real-time replication

Or use SQL:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
```

## Step 4: Start the Backend

```bash
python main.py
```

You should see:
```
Starting Glovy AI Agent backend...
Environment: development
Supabase URL: https://your-project.supabase.co
Subscribing to Supabase real-time messages...
Glovy backend is running and listening for messages...
```

## Step 5: Test It!

1. Open your frontend application
2. Start a chat session (match)
3. Send a message from one user
4. Watch the backend logs - Glovy will analyze the message
5. If conditions are met, Glovy will respond!
6. Check your frontend - Glovy's message should appear automatically

## Troubleshooting

### "Module not found" errors

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### "Connection refused" or Supabase errors

- Verify your `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check that your Supabase project is active
- Ensure real-time is enabled for the `messages` table

### Glovy not responding

- Check backend logs for errors
- Verify Google Gemini API key is valid
- Ensure message `sender_role` is not "Glovy" (Glovy ignores its own messages)
- Check that tone analysis threshold is met (adjust `GLOVY_RESPONSE_THRESHOLD` if needed)

### Real-time not working

- Verify real-time replication is enabled in Supabase
- Check network connectivity
- Ensure WebSocket connections are allowed

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [INTEGRATION.md](INTEGRATION.md) for frontend integration details
- Customize Glovy's persona and response behavior in `glovy_agent.py`
- Adjust response timing logic in `response_timing.py`

## Configuration Tips

### Make Glovy More Responsive

Lower the response threshold in `.env`:
```env
GLOVY_RESPONSE_THRESHOLD=0.5
GLOVY_MIN_MESSAGES_BEFORE_RESPONSE=1
```

### Make Glovy Less Responsive

Increase the threshold:
```env
GLOVY_RESPONSE_THRESHOLD=0.8
GLOVY_MIN_MESSAGES_BEFORE_RESPONSE=5
```

### Use Different Gemini Model

```env
GOOGLE_MODEL=gemini-1.0-pro  # Higher reasoning depth
# or
GOOGLE_MODEL=gemini-2.5-flash  # Faster, default
```

## Support

For issues:
1. Check the logs in the terminal
2. Verify all environment variables are set
3. Test Supabase connection separately
4. Review the integration guide

Happy chatting with Glovy! 🎉

