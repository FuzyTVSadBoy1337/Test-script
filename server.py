# 🍓 Blox Fruits Stats Tracker Server
# Advanced Python Flask server để track stats Blox Fruits players

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import threading
import webbrowser
import time
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# Database setup
DB_FILE = 'blox_fruits_stats.db'

def init_database():
    """Khởi tạo SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Player stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            user_id INTEGER,
            level INTEGER DEFAULT 0,
            beli INTEGER DEFAULT 0,
            fragments INTEGER DEFAULT 0,
            bounty INTEGER DEFAULT 0,
            honor INTEGER DEFAULT 0,
            equipped_fruit TEXT,
            fighting_style TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    ''')
    
    # Fighting styles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fighting_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            user_id INTEGER,
            style_name TEXT NOT NULL,
            owned BOOLEAN DEFAULT FALSE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Weapons/Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            user_id INTEGER,
            item_name TEXT NOT NULL,
            item_type TEXT, -- Sword, Gun, Fruit, etc.
            rarity TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Progress tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            user_id INTEGER,
            event_type TEXT, -- level_up, new_fruit, new_weapon, etc.
            old_value TEXT,
            new_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Khởi tạo database khi start
init_database()

# In-memory storage for real-time data
active_sessions = {}
recent_updates = []
max_recent_updates = 200

# HTML Template cho Blox Fruits Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍓 Blox Fruits Stats Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1c29 0%, #2d1b69 50%, #11998e 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            padding: 30px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-card h3 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #fff;
        }

        .stat-card p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .players-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }

        .player-card {
            background: linear-gradient(135deg, #ff7675, #6c5ce7);
            margin: 15px 0;
            padding: 20px;
            border-radius: 12px;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            align-items: center;
        }

        .player-info h4 {
            font-size: 1.4em;
            margin-bottom: 5px;
        }

        .player-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }

        .stat-item {
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 8px;
        }

        .weapons-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .weapon-list {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
        }

        .controls {
            text-align: center;
            margin: 20px 0;
        }

        .btn {
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            margin: 0 10px;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }

        .updates-feed {
            max-height: 400px;
            overflow-y: auto;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 15px;
        }

        .update-item {
            background: rgba(255,255,255,0.1);
            margin: 8px 0;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #4ecdc4;
        }

        .timestamp {
            color: #4ecdc4;
            font-size: 0.9em;
            font-weight: bold;
        }

        .rarity-legendary { color: #ff6b6b; font-weight: bold; }
        .rarity-mythical { color: #9b59b6; font-weight: bold; }
        .rarity-rare { color: #3498db; font-weight: bold; }
        .rarity-common { color: #95a5a6; }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        .live-indicator {
            animation: pulse 2s infinite;
            color: #2ecc71;
            font-weight: bold;
        }

        /* Recent Accounts Styles */
        .accounts-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .account-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .account-card:hover {
            transform: translateY(-3px);
            border-color: #4ecdc4;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }

        .account-card h4 {
            margin-bottom: 10px;
            color: #fff;
        }

        .account-stats-mini {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 0.9em;
        }

        /* Modal Styles */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: linear-gradient(135deg, #1a1c29 0%, #2d1b69 100%);
            border-radius: 20px;
            padding: 30px;
            max-width: 800px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }

        .close {
            font-size: 30px;
            cursor: pointer;
            color: #aaa;
            background: none;
            border: none;
        }

        .close:hover {
            color: #fff;
        }

        .account-details-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 25px;
        }

        .detail-section h3 {
            color: #4ecdc4;
            margin-bottom: 15px;
            font-size: 1.3em;
        }

        .stats-display {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }

        .item-tag {
            background: rgba(255,255,255,0.1);
            padding: 8px 12px;
            border-radius: 20px;
            text-align: center;
            font-size: 0.9em;
        }

        .item-sword { background: rgba(255, 107, 107, 0.3); }
        .item-gun { background: rgba(116, 185, 255, 0.3); }
        .fighting-style-owned { background: rgba(46, 204, 113, 0.3); }
        .fighting-style-not-owned { background: rgba(149, 165, 166, 0.3); }

        @media (max-width: 768px) {
            .accounts-container {
                grid-template-columns: 1fr;
            }
            
            .account-stats-mini {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍓 Blox Fruits Stats Tracker</h1>
            <p class="live-indicator">🔴 LIVE TRACKING ACTIVE</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>{{ total_players }}</h3>
                <p>👥 Tracked Players</p>
            </div>
            <div class="stat-card">
                <h3>{{ total_updates }}</h3>
                <p>📊 Total Updates</p>
            </div>
            <div class="stat-card">
                <h3>{{ avg_level }}</h3>
                <p>⭐ Average Level</p>
            </div>
            <div class="stat-card">
                <h3>{{ active_now }}</h3>
                <p>🎮 Active Now</p>
            </div>
        </div>

        <div class="controls">
            <button class="btn" onclick="refreshData()">🔄 Refresh</button>
            <button class="btn" onclick="toggleAutoRefresh()">⏱️ Auto Refresh</button>
            <button class="btn" onclick="exportData()">💾 Export Data</button>
            <button class="btn" onclick="clearData()">🗑️ Clear Data</button>
        </div>

        <div class="players-section">
            <h2>👑 Player Stats</h2>
            {% for player in active_players %}
            <div class="player-card">
                <div class="player-info">
                    <h4>🎮 {{ player.name }}</h4>
                    <p>🆔 ID: {{ player.user_id }}</p>
                    <p>⏰ Last: {{ player.last_update }}</p>
                </div>
                
                <div class="player-stats">
                    <div class="stat-item">
                        <strong>{{ player.level }}</strong><br>Level
                    </div>
                    <div class="stat-item">
                        <strong>{{ "{:,}".format(player.beli) }}</strong><br>💰 Beli
                    </div>
                    <div class="stat-item">
                        <strong>{{ "{:,}".format(player.fragments) }}</strong><br>💎 Fragments
                    </div>
                </div>
                
                <div class="weapons-section">
                    <div class="weapon-list">
                        <strong>⚔️ Fighting Style:</strong><br>
                        {{ player.fighting_style or "Unknown" }}
                    </div>
                    <div class="weapon-list">
                        <strong>🍓 Devil Fruit:</strong><br>
                        {{ player.equipped_fruit or "None" }}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="players-section">
            <h2>📈 Recent Accounts</h2>
            <div id="recent-accounts-container" class="accounts-container">
                <!-- Accounts sẽ được load bằng JavaScript -->
            </div>
            <div class="controls">
                <button id="show-all-btn" class="btn" style="display: none;" onclick="showAllAccounts()">
                    Hiển thị tất cả accounts
                </button>
            </div>
        </div>

        <!-- Account Details Modal -->
        <div id="account-modal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="modal-account-name"></h2>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="account-details-grid">
                        <div class="detail-section">
                            <h3>📊 Stats</h3>
                            <div class="stats-display">
                                <div class="stat-row">
                                    <span>Level:</span> <span id="modal-level"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Beli:</span> <span id="modal-beli"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Fragments:</span> <span id="modal-fragments"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Bounty:</span> <span id="modal-bounty"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Honor:</span> <span id="modal-honor"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Fighting Style:</span> <span id="modal-fighting-style"></span>
                                </div>
                                <div class="stat-row">
                                    <span>Equipped Fruit:</span> <span id="modal-equipped-fruit"></span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="detail-section">
                            <h3>⚔️ Fighting Styles</h3>
                            <div id="modal-fighting-styles" class="items-grid"></div>
                        </div>
                        
                        <div class="detail-section">
                            <h3>🗡️ Items</h3>
                            <div id="modal-items" class="items-grid"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let autoRefresh = false;
        let refreshInterval;
        let currentAccountsLimit = 10;

        function refreshData() {
            location.reload();
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = event.target;
            
            if (autoRefresh) {
                btn.textContent = '⏹️ Stop Auto';
                refreshInterval = setInterval(refreshData, 5000);
            } else {
                btn.textContent = '⏱️ Auto Refresh';
                clearInterval(refreshInterval);
            }
        }

        function exportData() {
            fetch('/api/export')
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'blox_fruits_stats.json';
                    a.click();
                });
        }

        function clearData() {
            if (confirm('Xóa tất cả dữ liệu tracking? Không thể hoàn tác!')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(() => location.reload());
            }
        }

        // Recent Accounts Functions
        document.addEventListener('DOMContentLoaded', function() {
            loadRecentAccounts();
        });

        function loadRecentAccounts(limit = 10) {
            fetch(`/api/recent-accounts?limit=${limit}`)
                .then(response => response.json())
                .then(data => {
                    displayRecentAccounts(data.accounts);
                    
                    const showAllBtn = document.getElementById('show-all-btn');
                    if (data.total_count > 10 && limit === 10) {
                        showAllBtn.style.display = 'inline-block';
                        showAllBtn.textContent = `Hiển thị tất cả ${data.total_count} accounts`;
                    } else {
                        showAllBtn.style.display = 'none';
                    }
                })
                .catch(error => console.error('Error loading accounts:', error));
        }

        function displayRecentAccounts(accounts) {
            const container = document.getElementById('recent-accounts-container');
            container.innerHTML = '';
            
            accounts.forEach(account => {
                const accountCard = document.createElement('div');
                accountCard.className = 'account-card';
                accountCard.onclick = () => showAccountDetails(account.name);
                
                accountCard.innerHTML = `
                    <h4>🎮 ${account.name}</h4>
                    <div class="account-stats-mini">
                        <div>Level: ${account.level}</div>
                        <div>Beli: ${account.beli.toLocaleString()}</div>
                        <div>Fragments: ${account.fragments.toLocaleString()}</div>
                        <div>Style: ${account.fighting_style || 'None'}</div>
                    </div>
                `;
                
                container.appendChild(accountCard);
            });
        }

        function showAllAccounts() {
            // Load tất cả accounts
            fetch('/api/recent-accounts?limit=1000')
                .then(response => response.json())
                .then(data => {
                    displayRecentAccounts(data.accounts);
                    document.getElementById('show-all-btn').style.display = 'none';
                });
        }

        function showAccountDetails(playerName) {
            fetch(`/api/account-details/${encodeURIComponent(playerName)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Không tìm thấy chi tiết account');
                        return;
                    }
                    
                    // Fill modal với data
                    document.getElementById('modal-account-name').textContent = data.name;
                    document.getElementById('modal-level').textContent = data.level.toLocaleString();
                    document.getElementById('modal-beli').textContent = data.beli.toLocaleString();
                    document.getElementById('modal-fragments').textContent = data.fragments.toLocaleString();
                    document.getElementById('modal-bounty').textContent = data.bounty.toLocaleString();
                    document.getElementById('modal-honor').textContent = data.honor.toLocaleString();
                    document.getElementById('modal-fighting-style').textContent = data.fighting_style || 'None';
                    document.getElementById('modal-equipped-fruit').textContent = data.equipped_fruit || 'None';
                    
                    // Fighting styles
                    const stylesContainer = document.getElementById('modal-fighting-styles');
                    stylesContainer.innerHTML = '';
                    data.fighting_styles.forEach(style => {
                        const styleElement = document.createElement('div');
                        styleElement.className = `item-tag ${style.owned ? 'fighting-style-owned' : 'fighting-style-not-owned'}`;
                        styleElement.textContent = `${style.name} ${style.owned ? '✅' : '❌'}`;
                        stylesContainer.appendChild(styleElement);
                    });
                    
                    // Items
                    const itemsContainer = document.getElementById('modal-items');
                    itemsContainer.innerHTML = '';
                    data.items.forEach(item => {
                        const itemElement = document.createElement('div');
                        itemElement.className = `item-tag item-${item.type.toLowerCase()}`;
                        itemElement.textContent = item.name;
                        itemsContainer.appendChild(itemElement);
                    });
                    
                    // Show modal
                    document.getElementById('account-modal').style.display = 'flex';
                })
                .catch(error => {
                    console.error('Error loading account details:', error);
                    alert('Lỗi khi tải chi tiết account');
                });
        }

        function closeModal() {
            document.getElementById('account-modal').style.display = 'none';
        }

        // Close modal khi click outside
        window.onclick = function(event) {
            const modal = document.getElementById('account-modal');
            if (event.target === modal) {
                closeModal();
            }
        }

        // Auto-refresh disabled by default
        // setTimeout(() => {
        //     document.querySelector('.btn').click();
        // }, 2000);
    </script>
</body>
</html>
"""

def save_player_stats(data):
    """Lưu player stats vào database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Insert player stats
    cursor.execute('''
        INSERT INTO player_stats 
        (player_name, user_id, level, beli, fragments, bounty, honor, equipped_fruit, fighting_style, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('player_name', ''),
        data.get('user_id', 0),
        data.get('level', 0),
        data.get('beli', 0),
        data.get('fragments', 0),
        data.get('bounty', 0),
        data.get('honor', 0),
        data.get('equipped_fruit', ''),
        data.get('fighting_style', ''),
        data.get('session_id', '')
    ))
    
    conn.commit()
    conn.close()

def save_fighting_styles(player_name, user_id, styles_data):
    """Lưu fighting styles data"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for style in styles_data.get('owned', []):
        cursor.execute('''
            INSERT OR REPLACE INTO fighting_styles 
            (player_name, user_id, style_name, owned)
            VALUES (?, ?, ?, ?)
        ''', (player_name, user_id, style, True))
    
    conn.commit()
    conn.close()

def save_player_items(player_name, user_id, items_data):
    """Lưu weapons/items data"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Clear old items for this player
    cursor.execute('DELETE FROM player_items WHERE player_name = ?', (player_name,))
    
    # Insert swords
    for sword in items_data.get('swords', []):
        cursor.execute('''
            INSERT INTO player_items (player_name, user_id, item_name, item_type)
            VALUES (?, ?, ?, ?)
        ''', (player_name, user_id, sword, 'Sword'))
    
    # Insert guns
    for gun in items_data.get('guns', []):
        cursor.execute('''
            INSERT INTO player_items (player_name, user_id, item_name, item_type)
            VALUES (?, ?, ?, ?)
        ''', (player_name, user_id, gun, 'Gun'))
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Main dashboard"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get active players (last 1 hour)
    one_hour_ago = datetime.now() - timedelta(hours=1)
    cursor.execute('''
        SELECT DISTINCT player_name, user_id, level, beli, fragments, 
               fighting_style, equipped_fruit, MAX(timestamp) as last_update
        FROM player_stats 
        WHERE timestamp > ?
        GROUP BY player_name
        ORDER BY last_update DESC
    ''', (one_hour_ago,))
    
    active_players = []
    for row in cursor.fetchall():
        active_players.append({
            'name': row[0],
            'user_id': row[1],
            'level': row[2],
            'beli': row[3],
            'fragments': row[4],
            'fighting_style': row[5],
            'equipped_fruit': row[6],
            'last_update': row[7]
        })
    
    # Get stats
    cursor.execute('SELECT COUNT(DISTINCT player_name) FROM player_stats')
    total_players = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM player_stats')
    total_updates = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(level) FROM player_stats WHERE timestamp > ?', (one_hour_ago,))
    avg_level = int(cursor.fetchone()[0] or 0)
    
    conn.close()
    
    return render_template_string(HTML_TEMPLATE,
                                total_players=total_players,
                                total_updates=total_updates,
                                avg_level=avg_level,
                                active_now=len(active_players),
                                active_players=active_players,
                                recent_updates=recent_updates[-20:])

@app.route('/api/recent-accounts')
def get_recent_accounts():
    """API để lấy recent accounts với pagination"""
    limit = request.args.get('limit', 10, type=int)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get recent accounts với thêm thông tin
    cursor.execute('''
        SELECT DISTINCT player_name, user_id, level, beli, fragments, 
               fighting_style, equipped_fruit, MAX(timestamp) as last_update
        FROM player_stats 
        GROUP BY player_name
        ORDER BY last_update DESC
        LIMIT ?
    ''', (limit,))
    
    accounts = []
    for row in cursor.fetchall():
        accounts.append({
            'name': row[0],
            'user_id': row[1], 
            'level': row[2],
            'beli': row[3],
            'fragments': row[4],
            'fighting_style': row[5],
            'equipped_fruit': row[6],
            'last_update': row[7]
        })
    
    # Get total count
    cursor.execute('SELECT COUNT(DISTINCT player_name) FROM player_stats')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'accounts': accounts,
        'total_count': total_count,
        'showing': len(accounts)
    })

@app.route('/api/account-details/<player_name>')
def get_account_details(player_name):
    """API để lấy chi tiết account bao gồm items"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get account basic info
    cursor.execute('''
        SELECT player_name, user_id, level, beli, fragments, 
               fighting_style, equipped_fruit, bounty, honor, timestamp
        FROM player_stats 
        WHERE player_name = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (player_name,))
    
    account_data = cursor.fetchone()
    if not account_data:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Get fighting styles
    cursor.execute('''
        SELECT style_name, owned FROM fighting_styles 
        WHERE player_name = ?
    ''', (player_name,))
    fighting_styles = [{'name': row[0], 'owned': bool(row[1])} for row in cursor.fetchall()]
    
    # Get weapons/items
    cursor.execute('''
        SELECT item_name, item_type FROM player_items 
        WHERE player_name = ?
    ''', (player_name,))
    items = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'name': account_data[0],
        'user_id': account_data[1],
        'level': account_data[2], 
        'beli': account_data[3],
        'fragments': account_data[4],
        'fighting_style': account_data[5],
        'equipped_fruit': account_data[6],
        'bounty': account_data[7],
        'honor': account_data[8],
        'last_update': account_data[9],
        'fighting_styles': fighting_styles,
        'items': items
    })

@app.route('/api/bloxfruits/stats', methods=['POST'])
def receive_bloxfruits_stats():
    """Nhận stats data từ Blox Fruits"""
    try:
        data = request.get_json()
        current_time = datetime.now()
        
        # Validate data
        if not data or not data.get('player_name'):
            return jsonify({'error': 'Invalid data'}), 400
        
        # Save to database
        save_player_stats(data)
        
        # Save fighting styles if provided
        if 'fighting_styles' in data:
            save_fighting_styles(data['player_name'], data.get('user_id', 0), data['fighting_styles'])
        
        # Save items if provided
        if 'items' in data:
            save_player_items(data['player_name'], data.get('user_id', 0), data['items'])
        
        # Update active sessions
        session_key = data['player_name']
        active_sessions[session_key] = {
            'last_update': current_time,
            'data': data
        }
        
        # Add to recent updates
        update_msg = f"Level {data.get('level', 0)} - {data.get('beli', 0):,} Beli"
        recent_updates.append({
            'timestamp': current_time.strftime("%H:%M:%S"),
            'player_name': data['player_name'],
            'message': update_msg
        })
        
        # Keep only recent updates
        if len(recent_updates) > max_recent_updates:
            recent_updates.pop(0)
        
        print(f"🍓 [{current_time.strftime('%H:%M:%S')}] Blox Fruits Stats Received:")
        print(f"   👤 Player: {data['player_name']} (ID: {data.get('user_id', 'Unknown')})")
        print(f"   ⭐ Level: {data.get('level', 0)} | 💰 Beli: {data.get('beli', 0):,}")
        print(f"   💎 Fragments: {data.get('fragments', 0):,} | ⚔️ Style: {data.get('fighting_style', 'None')}")
        print("   " + "-" * 60)
        
        return jsonify({
            'status': 'success',
            'message': 'Blox Fruits stats received successfully!',
            'timestamp': current_time.isoformat(),
            'player': data['player_name']
        })
        
    except Exception as e:
        print(f"❌ Error processing Blox Fruits stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export all data as JSON"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all data
    cursor.execute('SELECT * FROM player_stats ORDER BY timestamp DESC')
    stats = cursor.fetchall()
    
    cursor.execute('SELECT * FROM fighting_styles')
    styles = cursor.fetchall()
    
    cursor.execute('SELECT * FROM player_items')
    items = cursor.fetchall()
    
    conn.close()
    
    export_data = {
        'export_time': datetime.now().isoformat(),
        'player_stats': stats,
        'fighting_styles': styles,
        'player_items': items
    }
    
    return jsonify(export_data)

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Clear all tracking data"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM player_stats')
    cursor.execute('DELETE FROM fighting_styles')
    cursor.execute('DELETE FROM player_items')
    cursor.execute('DELETE FROM progress_log')
    
    conn.commit()
    conn.close()
    
    global recent_updates, active_sessions
    recent_updates.clear()
    active_sessions.clear()
    
    print("🗑️ All Blox Fruits tracking data cleared!")
    return jsonify({'status': 'success', 'message': 'All data cleared'})

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({
        'message': 'Blox Fruits Tracker Online!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'active_players': len(active_sessions)
    })

def open_browser():
    """Auto-open browser"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("🍓 Starting Blox Fruits Stats Tracker Server...")
    print("🌐 Dashboard: http://localhost:5000")
    print("📡 API Endpoint: http://localhost:5000/api/bloxfruits/stats")
    print("🎮 Ready to track Blox Fruits players!")
    print("=" * 60)
    
    # Auto-open browser
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=False)