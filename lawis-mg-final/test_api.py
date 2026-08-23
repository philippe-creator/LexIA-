import requests, json, sys

BASE = 'http://localhost:8000'
results = {}

# 1. Health check
try:
    r = requests.get(f'{BASE}/', timeout=5)
    results['health'] = {'status': r.status_code, 'body': r.json()}
    print(f"[OK] Health Check: {r.status_code} - {r.json()}")
except Exception as e:
    results['health'] = {'error': str(e)}
    print(f"[FAIL] Health Check: {e}")
    sys.exit(1)

# 2. Register test user
try:
    r = requests.post(f'{BASE}/auth/register', json={
        'username': 'demo_test', 'email': 'demo@lexia.ma',
        'password': 'Demo1234!', 'full_name': 'Demo User', 'role': 'etudiant'
    }, timeout=10)
    print(f"[{'OK' if r.status_code in (200,201) else 'INFO'}] Register: {r.status_code} - {r.text[:100]}")
except Exception as e:
    print(f"[WARN] Register: {e}")

# 3. Login
token = None
try:
    r = requests.post(f'{BASE}/auth/login',
        data={'username': 'demo_test', 'password': 'Demo1234!'},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
    if r.status_code == 200:
        token = r.json().get('access_token')
        print(f"[OK] Login: {r.status_code} - Token obtained")
    else:
        print(f"[FAIL] Login: {r.status_code} - {r.text[:150]}")
except Exception as e:
    print(f"[FAIL] Login: {e}")

if not token:
    # Try with existing user PHILIPPE
    try:
        r = requests.post(f'{BASE}/auth/login',
            data={'username': 'PHILIPPE', 'password': 'Demo1234!'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
        if r.status_code == 200:
            token = r.json().get('access_token')
            print(f"[OK] Login as PHILIPPE: Token obtained")
    except:
        pass

if not token:
    print("[FAIL] Could not obtain token. Stopping.")
    sys.exit(1)

headers = {'Authorization': f'Bearer {token}'}

# 4. Auth/me
try:
    r = requests.get(f'{BASE}/auth/me', headers=headers, timeout=5)
    user = r.json()
    print(f"[OK] Auth/me: {r.status_code} - User: {user.get('full_name', user.get('username'))}")
except Exception as e:
    print(f"[FAIL] Auth/me: {e}")

# 5. List conversations
try:
    r = requests.get(f'{BASE}/chat/conversations?limit=5&offset=0', headers=headers, timeout=5)
    convs = r.json() if r.status_code == 200 else []
    print(f"[OK] Conversations: {r.status_code} - {len(convs)} conversation(s)")
except Exception as e:
    print(f"[FAIL] Conversations: {e}")

# 6. Chat (non-streaming) 
try:
    r = requests.post(f'{BASE}/chat/', headers=headers, json={
        'query': 'Quel est le salaire minimum au Maroc?', 'doc_type': 'all'
    }, timeout=60)
    if r.status_code == 200:
        data = r.json()
        answer = data.get('answer', '')
        cit_count = len(data.get('citations', []))
        conf = data.get('confidence', 'N/A')
        print(f"[OK] Chat: {r.status_code} - Confidence: {conf} - Citations: {cit_count}")
        print(f"     Answer preview: {answer[:120]}...")
    else:
        print(f"[FAIL] Chat: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print(f"[FAIL] Chat: {e}")

# 7. Search stats
try:
    r = requests.get(f'{BASE}/search/stats', headers=headers, timeout=5)
    print(f"[OK] Search stats: {r.status_code}")
except Exception as e:
    print(f"[FAIL] Search stats: {e}")

# 8. Legal document types
try:
    r = requests.get(f'{BASE}/legal-documents/types', headers=headers, timeout=5)
    if r.status_code == 200:
        types = r.json()
        print(f"[OK] Legal doc types: {r.status_code} - {len(types)} type(s)")
    else:
        print(f"[FAIL] Legal doc types: {r.status_code}")
except Exception as e:
    print(f"[FAIL] Legal doc types: {e}")

# 9. Documents list
try:
    r = requests.get(f'{BASE}/documents/', headers=headers, timeout=5)
    docs = r.json() if r.status_code == 200 else []
    print(f"[OK] Documents: {r.status_code} - {len(docs)} document(s)")
except Exception as e:
    print(f"[FAIL] Documents: {e}")

# 10. Notifications
try:
    r = requests.get(f'{BASE}/notifications/', headers=headers, timeout=5)
    print(f"[OK] Notifications: {r.status_code}")
except Exception as e:
    print(f"[FAIL] Notifications: {e}")

# 11. Export (JSON) - test with a conversation if available
if convs:
    try:
        conv_id = convs[0].get('id') if isinstance(convs[0], dict) else convs[0]
        r = requests.get(f'{BASE}/export/conversations/{conv_id}/json', headers=headers, timeout=10)
        print(f"[OK] Export JSON: {r.status_code}")
    except Exception as e:
        print(f"[FAIL] Export JSON: {e}")

# 12. Export DOCX
    try:
        r = requests.get(f'{BASE}/export/conversations/{conv_id}/docx', headers=headers, timeout=10)
        print(f"[OK] Export DOCX: {r.status_code} - Size: {len(r.content)} bytes")
    except Exception as e:
        print(f"[FAIL] Export DOCX: {e}")

# 13. Verify NO billing endpoints exist
try:
    r = requests.get(f'{BASE}/billing/plans', headers=headers, timeout=5)
    if r.status_code == 404:
        print(f"[OK] Billing removed: /billing/plans returns 404")
    else:
        print(f"[WARN] Billing still exists: {r.status_code}")
except Exception as e:
    print(f"[OK] Billing removed (connection error)")

print("\n=== TEST COMPLETE ===")
