# Clear Production Database - Instructions

## Quick Guide to Clear BrainRush Production Database

There are two ways to clear your production database on Render:

---

## Method 1: Via Render Shell (Recommended)

### Steps:
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select your **BrainRush** web service
3. Click the **"Shell"** tab at the top
4. Run this command:
   ```bash
   python clear_database.py
   ```
5. Type `yes` when prompted
6. Done! ✅

**Pros**: Simple, no code changes needed  
**Cons**: Requires manual Render dashboard access

---

## Method 2: Via Secure HTTP Endpoint (One-Time Use)

### Setup (One Time):
1. Go to Render Dashboard → Your Web Service → **Environment**
2. Add this environment variable:
   ```
   Key: ADMIN_CLEAR_TOKEN
   Value: <generate-a-random-secret-here>
   ```
   Example value: `clear-brainrush-2025-xyz789`
3. Save and wait for automatic redeploy (~2 minutes)

### Clear Database:
Visit this URL in your browser:
```
https://your-app-name.onrender.com/admin/clear-database?token=YOUR_SECRET_TOKEN
```

Replace:
- `your-app-name` with your actual Render app name
- `YOUR_SECRET_TOKEN` with the token you set above

You'll see a JSON response like:
```json
{
  "success": true,
  "message": "Database cleared successfully",
  "deleted": {
    "scores": 42,
    "users": 15
  }
}
```

### Security (Important!):
After clearing the database, **remove the `ADMIN_CLEAR_TOKEN` environment variable** to disable the endpoint.

**Pros**: Can be done from anywhere, no Render dashboard needed  
**Cons**: Requires environment variable setup and removal

---

## What Gets Deleted?

Both methods delete:
- ✅ All user accounts
- ✅ All quiz scores
- ✅ All dashboard history
- ✅ All leaderboard data

The database structure (tables, indexes) remains intact - only the data is cleared.

---

## After Clearing

Your friends will see:
- Fresh BrainRush landing page
- No existing users or scores
- Clean leaderboard
- Ready to register and compete!

---

## Recommendation

For a one-time clear before sharing with friends, use **Method 1 (Render Shell)** - it's simpler and doesn't require code deployment.

Use **Method 2** only if you need to clear the database frequently or want remote access without logging into Render.
