# Test API Endpoints

## Issue: "Not Found: /api/tasks/promo-code/"

### Possible Causes:
1. ✅ URL pattern exists in tasks/urls.py
2. ✅ View function exists in tasks/views.py
3. ⚠️ Trailing slash issue
4. ⚠️ CORS preflight request

### Solution Applied:
1. Added APPEND_SLASH = True in settings.py
2. Added alternative URL without trailing slash
3. Restarted server required

### How to Test:

#### 1. Restart Backend Server:
```bash
# Stop the server (Ctrl+C)
cd backend
python manage.py runserver
```

#### 2. Test with curl:
```bash
# Test promo code endpoint
curl -X POST http://localhost:8000/api/tasks/promo-code/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -d '{"code": "WELCOME2024"}'
```

#### 3. Test in Browser Console:
```javascript
// Get your token first
const token = localStorage.getItem('token');

// Test promo code
fetch('http://localhost:8000/api/tasks/promo-code/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Token ${token}`
  },
  body: JSON.stringify({ code: 'WELCOME2024' })
})
.then(r => r.json())
.then(d => console.log(d))
.catch(e => console.error(e));
```

### Expected Response:
```json
{
  "message": "Promo code redeemed",
  "amount": 2.00
}
```

### All Task Endpoints:

1. **GET /api/tasks/** - List all tasks
   - Auth: Required
   - Method: GET

2. **POST /api/tasks/start/** - Start a task
   - Auth: Required
   - Method: POST
   - Body: `{"task_id": 1}`

3. **POST /api/tasks/complete/** - Complete a task
   - Auth: Required
   - Method: POST
   - Body: `{"task_id": 1, "verification_input": ""}`

4. **GET /api/tasks/my-tasks/** - Get user's tasks
   - Auth: Required
   - Method: GET

5. **POST /api/tasks/daily-bonus/** - Claim daily bonus
   - Auth: Required
   - Method: POST
   - Body: `{}`

6. **POST /api/tasks/promo-code/** - Redeem promo code
   - Auth: Required
   - Method: POST
   - Body: `{"code": "WELCOME2024"}`

### Verify URLs are Registered:
```bash
cd backend
python manage.py show_urls | grep tasks
```

Or check manually:
```python
python manage.py shell
from django.urls import get_resolver
resolver = get_resolver()
for pattern in resolver.url_patterns:
    print(pattern)
```

### Common Issues:

#### Issue 1: "Not Found" Error
**Cause:** URL pattern mismatch
**Solution:** 
- Check trailing slash
- Restart server
- Clear browser cache

#### Issue 2: "OPTIONS" Request Failing
**Cause:** CORS preflight
**Solution:** Already configured in settings.py

#### Issue 3: "401 Unauthorized"
**Cause:** Missing or invalid token
**Solution:** 
- Login again
- Check token in localStorage
- Verify token format: `Token <your-token>`

#### Issue 4: "405 Method Not Allowed"
**Cause:** Wrong HTTP method
**Solution:** Use POST for promo-code endpoint

### Debug Steps:

1. **Check if URL is registered:**
```bash
python manage.py show_urls
```

2. **Check server logs:**
Look for the actual error in terminal where server is running

3. **Test without frontend:**
Use curl or Postman to test API directly

4. **Check CORS:**
```python
# In settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

### Quick Fix:

If still not working, try this:

1. **Stop backend server** (Ctrl+C)

2. **Clear Python cache:**
```bash
cd backend
Remove-Item -Recurse -Force __pycache__
Remove-Item -Recurse -Force tasks\__pycache__
```

3. **Restart server:**
```bash
python manage.py runserver
```

4. **Test again in frontend**

### Frontend Code Check:

Make sure in `frontend/src/pages/Tasks.jsx`:
```javascript
const redeemPromo = async () => {
  try {
    const response = await api.post('/tasks/promo-code/', { code: promoCode });
    // Note: URL should be '/tasks/promo-code/' not '/tasks/promo-code'
    setMessage(`✅ ${response.data.message}! You earned $${response.data.amount}`);
    setPromoCode('');
  } catch (error) {
    setMessage(error.response?.data?.error || 'Failed to redeem promo code');
  }
};
```

### Success Indicators:

✅ Server logs show: `"POST /api/tasks/promo-code/ HTTP/1.1" 200`
✅ Frontend shows success message
✅ Balance increases
✅ Transaction appears in history

---

**After applying fixes, restart backend server and test again!**
