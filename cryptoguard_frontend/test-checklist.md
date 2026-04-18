# CryptoGuard Testing Checklist

## Pre-Flight Checks
- [ ] Flask backend is running on http://127.0.0.1:5000
- [ ] Database file `transactions.db` exists and is accessible
- [ ] No browser console errors on page load
- [ ] Network tab shows successful API calls

## Dashboard Functionality Tests

### 1. Market Chart & Dynamic Labels
- [ ] Chart loads with BTC data by default
- [ ] Dropdown changes chart from BTC → ETH → ADA
- [ ] Chart subtitle updates: "BTC/USD" → "ETH/USD" → "ADA/USD"
- [ ] Chart shows live data (not static sample data)
- [ ] No "Market data temporarily unavailable" message

### 2. Live Market Prices Panel
- [ ] All 5 coins show prices: BTC, ETH, ADA, SOL, BNB
- [ ] Prices update every 30 seconds
- [ ] 24h change percentages show correctly (green/red)
- [ ] Hover effects work on price cards

### 3. Portfolio Holdings
- [ ] Holdings display shows correct amounts
- [ ] Updates after adding transactions
- [ ] Shows "No holdings yet" when appropriate
- [ ] Decimal precision (6 places) works correctly

### 4. Transaction History Table
- [ ] Table headers: Date | Asset | Type | Amount | Price
- [ ] Transactions appear in correct order (newest first)
- [ ] Buy transactions show in green, Sell in red
- [ ] Table updates immediately after new transactions
- [ ] Handles empty state correctly

### 5. Portfolio Pie Chart
- [ ] Chart renders with correct colors
- [ ] Shows percentages correctly
- [ ] Updates after transactions
- [ ] Handles empty portfolio with message
- [ ] Tooltips show amounts and percentages

### 6. Total Portfolio Value
- [ ] Shows correct total USD value
- [ ] 24h change percentage displays
- [ ] Updates with live price changes
- [ ] Color coding: green (profit), red (loss), gray (neutral)

### 7. Transaction Form Validation
- [ ] Prevents negative amounts
- [ ] Prevents empty inputs
- [ ] Prevents past dates with error message
- [ ] Prevents selling more than owned
- [ ] Shows specific error messages
- [ ] Form clears after successful transaction

### 8. API Error Handling
- [ ] Shows "Market data temporarily unavailable" on API failure
- [ ] Application doesn't crash on network errors
- [ ] Fallback to static data when needed
- [ ] Console shows helpful error messages

## Debug Console Commands

### Check API Endpoints
```javascript
// In browser console
fetch('http://127.0.0.1:5000/transactions', {headers: {'X-Auth-Token': 'your_token'}})
.then(r => r.json()).then(console.log)
```

### Check Market API
```javascript
// Test CoinGecko API
fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,cardano,solana,binancecoin&vs_currencies=usd&include_24hr_change=true')
.then(r => r.json()).then(console.log)
```

### Check Chart Data
```javascript
// In browser console
console.log('Current chart coin:', currentChartCoin);
console.log('Market prices data:', marketPricesData);
```

## Common Issues & Solutions

### Issue: Chart not updating on coin change
**Check:** Event listener attached to dropdown
**Solution:** Verify dropdown element has correct ID and event listener

### Issue: Market prices not loading
**Check:** CORS issues, API rate limits
**Solution:** Check network tab for failed requests

### Issue: Portfolio value not calculating
**Check:** Transaction data format, price data availability
**Solution:** Verify API responses and data parsing

### Issue: Transaction form not submitting
**Check:** Backend validation, authentication
**Solution:** Check Flask logs and browser network tab

## Performance Monitoring
- [ ] Initial page load < 3 seconds
- [ ] Market price updates < 1 second
- [ ] Transaction submission < 2 seconds
- [ ] Chart rendering < 2 seconds

## Data Verification
After testing, verify:
- [ ] Portfolio calculations match manual calculations
- [ ] Transaction history matches database
- [ ] Market prices match CoinGecko website
- [ ] No duplicate API calls
- [ ] Memory leaks (chart instances properly cleaned up)
