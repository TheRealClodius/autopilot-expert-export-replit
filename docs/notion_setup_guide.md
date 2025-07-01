# Notion Dashboard Integration Setup Guide

## Step 1: Get Your Integration Token

1. **Go to**: https://www.notion.so/my-integrations
2. **Click on your integration name** (not "New integration")
3. **Find "Internal Integration Token"** section
4. **Copy the token** - it should look like:
   ```
   secret_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
   ```
   **Important**: Must start with `secret_` and be about 50 characters long

## Step 2: Get Your Database ID

1. **Open your Notion database** in your browser
2. **Look at the URL** - it will look like:
   ```
   https://www.notion.so/yourworkspace/Database-Name-1234567890abcdef1234567890abcdef?v=...
   ```
3. **Copy the 32-character string** right before the `?v=` part
   - Example: `1234567890abcdef1234567890abcdef`
   - Must be exactly 32 characters (letters and numbers)

## Step 3: Connect Integration to Database

1. **In your Notion database**, click the three dots `...` in the top right
2. **Click "Connections"**
3. **Find your integration** in the list and click to add it
4. **Confirm** the integration now appears under "Connected to"

## Current Values Check

Based on your current setup:
- **Integration Token**: ❌ Doesn't start with `secret_`
- **Database ID**: ❌ `22366b7e03168013a4ddef9a67f7e10` (31 chars, need 32)
- **Missing Character**: The database ID is missing 1 character from the end

## Next Steps

1. Update both secrets with the correct format
2. Ensure integration is connected to database
3. Test the connection