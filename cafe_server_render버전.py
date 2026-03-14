from flask import Flask, request, jsonify, render_template_string
import sqlite3
import hashlib
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cafe_server_secret_key_2024'

DB_PATH = "cafe_users.db"

# ========================
# 데이터베이스 초기화
# ========================
def init_db():
    """사용자 데이터베이스 초기화"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP
            )
        """)
        # 기본 관리자
        cursor.execute("INSERT INTO users (username, password, status) VALUES (?, ?, 'approved')",
                      ("admin", hashlib.sha256("admin1234".encode()).hexdigest()))
        conn.commit()
        conn.close()

def hash_password(password):
    """비밀번호 해시"""
    return hashlib.sha256(password.encode()).hexdigest()

# ========================
# API: 회원가입
# ========================
@app.route('/api/register', methods=['POST'])
def api_register():
    """사용자 회원가입"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "아이디와 비밀번호를 입력하세요"}), 400
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, status) VALUES (?, ?, 'pending')",
                          (username, hash_password(password)))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": f"{username} 가입 신청 완료! 관리자 승인을 기다려주세요."}), 200
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "이미 존재하는 아이디입니다"}), 400
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# API: 로그인
# ========================
@app.route('/api/login', methods=['POST'])
def api_login():
    """사용자 로그인 (승인된 사용자만)"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "아이디와 비밀번호를 입력하세요"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password, status FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({"success": False, "message": "등록되지 않은 아이디입니다"}), 401
        
        stored_password, status = result
        
        # 상태 확인
        if status == "pending":
            return jsonify({"success": False, "message": "가입 승인 대기 중입니다. 관리자 승인을 기다려주세요."}), 401
        elif status == "rejected":
            return jsonify({"success": False, "message": "가입이 거절되었습니다."}), 401
        elif status != "approved":
            return jsonify({"success": False, "message": "비활성화된 계정입니다"}), 401
        
        # 비밀번호 확인
        if stored_password == hash_password(password):
            return jsonify({"success": True, "message": "로그인 성공", "username": username}), 200
        else:
            return jsonify({"success": False, "message": "비밀번호가 틀렸습니다"}), 401
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# API: 가입 요청 목록
# ========================
@app.route('/api/get_pending_users', methods=['POST'])
def api_get_pending_users():
    """관리자가 가입 대기 중인 사용자 조회"""
    try:
        data = request.get_json()
        admin_password = data.get('admin_password')
        
        if admin_password != "admin1234":
            return jsonify({"success": False, "message": "관리자 비밀번호가 틀렸습니다"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, status, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        conn.close()
        
        user_list = [{
            "username": u[0], 
            "status": u[1],
            "created_at": u[2]
        } for u in users if u[0] != "admin"]
        
        return jsonify({"success": True, "users": user_list}), 200
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# API: 가입 승인
# ========================
@app.route('/api/approve_user', methods=['POST'])
def api_approve_user():
    """관리자가 사용자 승인"""
    try:
        data = request.get_json()
        username = data.get('username')
        admin_password = data.get('admin_password')
        
        if admin_password != "admin1234":
            return jsonify({"success": False, "message": "관리자 비밀번호가 틀렸습니다"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": f"{username} 승인 완료"}), 200
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# API: 가입 거절
# ========================
@app.route('/api/reject_user', methods=['POST'])
def api_reject_user():
    """관리자가 사용자 거절"""
    try:
        data = request.get_json()
        username = data.get('username')
        admin_password = data.get('admin_password')
        
        if admin_password != "admin1234":
            return jsonify({"success": False, "message": "관리자 비밀번호가 틀렸습니다"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'rejected' WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": f"{username} 거절 완료"}), 200
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# API: 사용자 삭제
# ========================
@app.route('/api/delete_user', methods=['POST'])
def api_delete_user():
    """관리자가 사용자 삭제"""
    try:
        data = request.get_json()
        username = data.get('username')
        admin_password = data.get('admin_password')
        
        if admin_password != "admin1234":
            return jsonify({"success": False, "message": "관리자 비밀번호가 틀렸습니다"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": f"{username} 삭제 완료"}), 200
    
    except Exception as e:
        return jsonify({"success": False, "message": f"오류: {str(e)}"}), 500

# ========================
# 웹 관리 페이지
# ========================
ADMIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>네이버카페 자동가입 - 관리자</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 30px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #666; font-size: 18px; margin-bottom: 15px; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .user-list { margin-top: 20px; }
        .user-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; }
        .user-info { flex: 1; }
        .user-name { font-weight: bold; font-size: 16px; }
        .user-status { padding: 4px 12px; border-radius: 4px; font-size: 12px; margin-top: 5px; display: inline-block; }
        .pending { background: #fff3cd; color: #856404; }
        .approved { background: #d4edda; color: #155724; }
        .rejected { background: #f8d7da; color: #721c24; }
        .user-buttons { display: flex; gap: 5px; }
        button { padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .approve { background: #28a745; color: white; }
        .approve:hover { background: #218838; }
        .reject { background: #dc3545; color: white; }
        .reject:hover { background: #c82333; }
        .delete { background: #6c757d; color: white; }
        .delete:hover { background: #5a6268; }
        .message { padding: 12px; border-radius: 4px; margin-bottom: 15px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 네이버카페 자동가입 - 관리자</h1>
        
        <div id="message"></div>
        
        <!-- 가입 요청 섹션 -->
        <div class="section">
            <h2>📋 가입 요청 (승인 대기 중)</h2>
            <div class="user-list" id="pendingList">로딩 중...</div>
        </div>
        
        <!-- 모든 사용자 섹션 -->
        <div class="section">
            <h2>👥 전체 사용자</h2>
            <div class="user-list" id="userList">로딩 중...</div>
        </div>
    </div>

    <script>
        const SERVER_URL = window.location.origin;
        
        function showMessage(text, isSuccess) {
            const msgDiv = document.getElementById('message');
            msgDiv.textContent = text;
            msgDiv.className = isSuccess ? 'message success' : 'message error';
            setTimeout(() => msgDiv.className = '', 3000);
        }
        
        async function loadUsers() {
            const adminPassword = prompt('관리자 비밀번호:');
            if (!adminPassword) return;
            
            try {
                const res = await fetch(`${SERVER_URL}/api/get_pending_users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ admin_password: adminPassword })
                });
                const data = await res.json();
                
                if (!data.success) {
                    showMessage(data.message, false);
                    return;
                }
                
                // 가입 요청 (pending)
                const pendingUsers = data.users.filter(u => u.status === 'pending');
                const pendingList = document.getElementById('pendingList');
                if (pendingUsers.length === 0) {
                    pendingList.innerHTML = '<p style="color: #999;">가입 요청이 없습니다.</p>';
                } else {
                    pendingList.innerHTML = pendingUsers.map(user => `
                        <div class="user-item">
                            <div class="user-info">
                                <div class="user-name">${user.username}</div>
                                <span class="user-status pending">⏳ 대기 중</span>
                            </div>
                            <div class="user-buttons">
                                <button class="approve" onclick="approveUser('${user.username}', '${adminPassword}')">승인</button>
                                <button class="reject" onclick="rejectUser('${user.username}', '${adminPassword}')">거절</button>
                            </div>
                        </div>
                    `).join('');
                }
                
                // 전체 사용자
                const userList = document.getElementById('userList');
                userList.innerHTML = data.users.map(user => {
                    let statusClass = user.status;
                    let statusText = {
                        'approved': '✓ 승인됨',
                        'pending': '⏳ 대기 중',
                        'rejected': '✗ 거절됨'
                    }[user.status] || '불명';
                    
                    return `
                        <div class="user-item">
                            <div class="user-info">
                                <div class="user-name">${user.username}</div>
                                <span class="user-status ${statusClass}">${statusText}</span>
                            </div>
                            <div class="user-buttons">
                                <button class="delete" onclick="deleteUser('${user.username}', '${adminPassword}')">삭제</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                showMessage('오류: ' + e, false);
            }
        }
        
        async function approveUser(username, adminPassword) {
            try {
                const res = await fetch(`${SERVER_URL}/api/approve_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, admin_password: adminPassword })
                });
                const data = await res.json();
                showMessage(data.message, data.success);
                if (data.success) loadUsers();
            } catch (e) {
                showMessage('오류: ' + e, false);
            }
        }
        
        async function rejectUser(username, adminPassword) {
            try {
                const res = await fetch(`${SERVER_URL}/api/reject_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, admin_password: adminPassword })
                });
                const data = await res.json();
                showMessage(data.message, data.success);
                if (data.success) loadUsers();
            } catch (e) {
                showMessage('오류: ' + e, false);
            }
        }
        
        async function deleteUser(username, adminPassword) {
            if (!confirm(`${username}을(를) 삭제하시겠습니까?`)) return;
            
            try {
                const res = await fetch(`${SERVER_URL}/api/delete_user`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, admin_password: adminPassword })
                });
                const data = await res.json();
                showMessage(data.message, data.success);
                if (data.success) loadUsers();
            } catch (e) {
                showMessage('오류: ' + e, false);
            }
        }
        
        window.onload = loadUsers;
    </script>
</body>
</html>
"""

@app.route('/admin', methods=['GET'])
def admin_page():
    """관리자 페이지"""
    return render_template_string(ADMIN_PAGE_HTML)

# ========================
# 서버 실행
# ========================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 서버 시작!")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
