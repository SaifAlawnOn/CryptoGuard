// Debug script for CryptoGuard testing
// Paste this in browser console to test functionality

function debugCryptoGuard() {
    console.log('=== CryptoGuard Debug Check ===');
    
    // Check if we're logged in
    const token = localStorage.getItem('cryptoguard_token');
    console.log('Auth token exists:', !!token);
    
    // Check API connectivity
    fetch('http://127.0.0.1:5000/me', {
        headers: token ? {'X-Auth-Token': token} : {}
    })
    .then(r => r.json())
    .then(data => console.log('Auth check:', data))
    .catch(e => console.error('Auth error:', e));
    
    // Check market prices API
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,cardano,solana,binancecoin&vs_currencies=usd&include_24hr_change=true')
    .then(r => r.json())
    .then(data => console.log('Market prices:', data))
    .catch(e => console.error('Market prices error:', e));
    
    // Check transactions
    if (token) {
        fetch('http://127.0.0.1:5000/transactions', {
            headers: {'X-Auth-Token': token}
        })
        .then(r => r.json())
        .then(data => console.log('Transactions:', data))
        .catch(e => console.error('Transactions error:', e));
    }
    
    // Test form validation
    const coinSelect = document.getElementById('coin');
    const amountInput = document.getElementById('amount');
    const typeSelect = document.getElementById('type');
    const dateInput = document.getElementById('date');
    
    console.log('Form elements found:', {
        coin: !!coinSelect,
        amount: !!amountInput,
        type: !!typeSelect,
        date: !!dateInput
    });
    
    // Test chart functions
    console.log('Chart functions available:', {
        initMarketChart: typeof initMarketChart,
        loadMarketPrices: typeof loadMarketPrices,
        updatePortfolioPieChart: typeof updatePortfolioPieChart
    });
    
    console.log('=== End Debug Check ===');
}

// Quick test functions
function testTransaction() {
    console.log('Testing transaction add...');
    const testData = {
        coin: 'BTC',
        amount: '0.001',
        type: 'buy',
        date: new Date().toISOString().split('T')[0]
    };
    
    fetch('http://127.0.0.1:5000/add_transaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Auth-Token': localStorage.getItem('cryptoguard_token')
        },
        body: JSON.stringify(testData)
    })
    .then(r => r.json())
    .then(data => console.log('Transaction test result:', data))
    .catch(e => console.error('Transaction test error:', e));
}

function testChartUpdate() {
    console.log('Testing chart update...');
    const coinSelect = document.getElementById('coin');
    if (coinSelect) {
        coinSelect.value = 'ETH';
        coinSelect.dispatchEvent(new Event('change'));
        setTimeout(() => console.log('Chart should now show ETH data'), 2000);
    }
}

// Run debug check
debugCryptoGuard();

// Export functions for manual testing
window.debugCryptoGuard = debugCryptoGuard;
window.testTransaction = testTransaction;
window.testChartUpdate = testChartUpdate;
