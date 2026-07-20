# GitHub Actions Setup for Automated Data Collection

## Step 1: Add Repository Secrets

Go to your repository settings:
https://github.com/rahulmehta25/MARTA/settings/secrets/actions

Click "New repository secret" and add these THREE secrets:

### Secret 1: MARTA_API_KEY
```
Name: MARTA_API_KEY
Value: ff98ada7-0436-42c5-b9bf-1071245ad1a0
```

### Secret 2: SUPABASE_URL
```
Name: SUPABASE_URL
Value: https://vglychbweuowsovboxyf.supabase.co
```

### Secret 3: SUPABASE_SERVICE_KEY
```
Name: SUPABASE_SERVICE_KEY
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjY5MDk5MywiZXhwIjoyMDcyMjY2OTkzfQ.g65JH484ZiQ17phNpPnyhlco5XnopjyJegIWD15kQ8Q
```

⚠️ **IMPORTANT**: The SERVICE_KEY is sensitive! Only add it to GitHub Secrets, never commit it to code.

## Step 2: Update the Workflow

The workflow file is already created at `.github/workflows/collect_data_supabase.yml`

Let me update it to use the secure collection script: