# How to Get Your Supabase Service Role Key

## Why You Need It
With the secure RLS policies, the anon key can only READ data. To WRITE data (insert arrivals, update stations), you need the service role key.

## Steps to Get Service Role Key

1. **Go to Supabase API Settings**:
   https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/settings/api

2. **Find the Service Role Key**:
   - Look for the section labeled "service_role"
   - It will be a longer JWT token similar to your anon key
   - Click the "Reveal" button to see it
   - Copy the entire key

3. **Add to .env.supabase**:
   ```bash
   # Add this line to your .env.supabase file:
   SUPABASE_SERVICE_KEY=eyJ... (your service role key here)
   ```

4. **Test with Secure Collection**:
   ```bash
   source venv/bin/activate
   export $(cat .env.supabase | grep -v '^#' | xargs)
   python3 collect_data_secure.py
   ```

## Alternative: Allow Anon Key to Write

If you can't get the service role key or prefer simplicity, run this SQL to allow the anon key to write:

```sql
-- Allow anon users to write (less secure but simpler)
DROP POLICY IF EXISTS "Service role can insert arrivals" ON arrivals;
DROP POLICY IF EXISTS "Service role can manage stations" ON stations;

CREATE POLICY "Anon can insert arrivals" ON arrivals
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Anon can manage stations" ON stations
    FOR ALL USING (true) WITH CHECK (true);
```

## Security Comparison

### Using Service Role Key (Recommended):
- ✅ More secure - anon key stays read-only
- ✅ Better for production
- ❌ Requires managing two keys

### Allowing Anon Writes:
- ✅ Simpler - one key for everything
- ✅ Works with current setup
- ❌ Less secure - anyone with anon key can write

## For GitHub Actions

Once you have the service role key, add it to GitHub secrets:
1. Go to: https://github.com/rahulmehta25/MARTA/settings/secrets/actions
2. Add new secret: `SUPABASE_SERVICE_KEY`
3. Update the workflow to use it