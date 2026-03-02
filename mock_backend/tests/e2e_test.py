import asyncio
import datetime
import json
import uuid
import requests
import concurrent.futures
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.security import get_password_hash
import urllib.parse

from websockets.sync.client import connect

BASE_URL = "http://127.0.0.1:8000"
DB_URL = "postgresql+asyncpg://postgres:Password%401548@localhost:5432/interview_db"

results = {
    "Overall System Health": "PASS",
    "Concurrency Integrity": "PASS",
    "Transaction Integrity": "PASS",
    "Auth Integrity": "PASS",
    "WebSocket Integrity": "PASS",
}

def report_fail(category):
    global results
    results[category] = "FAIL"
    results["Overall System Health"] = "FAIL"

def step_print(name, endpoint, payload, status, body, db_result, test_status, test_category=None):
    if test_status == "FAIL" and test_category:
        report_fail(test_category)

    print(f"\n1. Test Name: {name}")
    print(f"2. Endpoint: {endpoint}")
    print(f"3. Request Payload: {json.dumps(payload)}")
    print(f"4. Response Status: {status}")
    print(f"5. Response Body: {json.dumps(body) if isinstance(body, dict) else body}")
    print(f"6. DB Validation Result: {db_result}")
    print(f"7. {test_status}")

async def async_db_query(query, params=None):
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text(query), params or {})
        if result.returns_rows:
            return result.fetchall()
        return None

async def override_candidate_password(candidate_id: str, plain_password: str):
    hashed = get_password_hash(plain_password)
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET hashed_password = :hpw WHERE id = :id"),
            {"hpw": hashed, "id": candidate_id}
        )

async def seed_template_and_questions():
    template_id = str(uuid.uuid4())
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            INSERT INTO interview_templates (id, title, description, is_active, settings)
            VALUES (:id, 'Backend Developer', 'A standard template', true, '{}')
            ON CONFLICT DO NOTHING
            """), {"id": template_id}
        )
        for i in range(3):
            await conn.execute(
                text("""
                INSERT INTO template_questions (id, template_id, question_text, question_type, time_limit_sec, "order")
                VALUES (:id, :t_id, :q_text, 'technical', 60, :ord)
                """), {
                    "id": str(uuid.uuid4()),
                    "t_id": template_id,
                    "q_text": f"Question {i+1}",
                    "ord": i
                }
            )
    return template_id

def run_tests():
    print("-----------------------------------")
    print("PHASE 1 - AUTH VALIDATION")
    print("-----------------------------------")

    # 1. Login Admin
    req = {"username": "admin", "password": "admin123"}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login/admin", json=req)
    admin_token = ""
    admin_login_status = "PASS" if resp.status_code == 200 else "FAIL"
    if resp.status_code == 200:
        admin_token = resp.json().get("access_token")
    step_print("Admin Login", "POST /api/v1/auth/login/admin", req, resp.status_code, resp.json() if resp.text else "", "N/A", admin_login_status, "Auth Integrity")

    # 2. Register Candidate
    cand_email = f"c{uuid.uuid4().hex[:6]}@example.com"
    data = {"candidate_name": "Test Candidate", "candidate_email": cand_email, "job_description": "Dev"}
    files = {"resume": ("resume.pdf", b"pdf mock", "application/pdf")}
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    resp_cand = requests.post(f"{BASE_URL}/api/v1/auth/admin/register-candidate", data=data, files=files, headers=headers)
    register_status = "PASS" if resp_cand.status_code == 201 else "FAIL"
    cand_id = resp_cand.json().get("id", "")
    step_print("Register Candidate", "POST /api/v1/auth/admin/register-candidate", data, resp_cand.status_code, resp_cand.json() if resp_cand.text else "", "Candidate inserted", register_status, "Auth Integrity")

    if not cand_id:
        print("Test stopped: failed to register candidate")
        return

    # Set known password
    cand_password = "password123"
    asyncio.run(override_candidate_password(cand_id, cand_password))

    # 3. Login Candidate
    req_c = {"username": cand_email.split('@')[0], "password": cand_password}
    resp_cl = requests.post(f"{BASE_URL}/api/v1/auth/login/candidate", json=req_c)
    cand_token = resp_cl.json().get("access_token", "") if resp_cl.status_code == 200 else ""
    c_login_status = "PASS" if resp_cl.status_code == 200 else "FAIL"
    step_print("Candidate Login", "POST /api/v1/auth/login/candidate", req_c, resp_cl.status_code, resp_cl.json() if resp_cl.text else "", "N/A", c_login_status, "Auth Integrity")

    # Validate JWT logic
    import urllib.parse
    import base64
    def b64_decode(s):
        s += '=' * (-len(s) % 4)
        return json.loads(base64.b64decode(s).decode())
    
    jwt_status = "FAIL"
    try:
         payload = b64_decode(cand_token.split(".")[1])
         uuid.UUID(payload["sub"])
         jwt_status = "PASS"
    except Exception as e:
         pass
    step_print("Validate JWT format", "N/A", {}, "N/A", "N/A", "sub is UUID", jwt_status, "Auth Integrity")

    # Negative test
    tampered = cand_token[:-3] + "tam"
    headers_t = {"Authorization": f"Bearer {tampered}"}
    resp_nt = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers_t)
    nt_status = "PASS" if resp_nt.status_code == 401 else "FAIL"
    step_print("Negative test: Tampered JWT", "GET /api/v1/auth/me", {}, resp_nt.status_code, resp_nt.json() if resp_nt.text else "", "N/A", nt_status, "Auth Integrity")


    print("-----------------------------------")
    print("PHASE 2 - TEMPLATE VALIDATION")
    print("-----------------------------------")
    # Seed template manually, verify from DB
    template_id = asyncio.run(seed_template_and_questions())
    db_templates = asyncio.run(async_db_query("SELECT id FROM interview_templates WHERE id = :t_id", {"t_id": template_id}))
    db_questions = asyncio.run(async_db_query("SELECT id FROM template_questions WHERE template_id = :t_id", {"t_id": template_id}))
    
    t_status = "PASS" if db_templates and len(db_questions) == 3 else "FAIL"
    step_print("Seed Interview Template", "DB Insert", {"template_id": template_id}, "N/A", "N/A", f"Template + {len(db_questions)} questions found", t_status, "Transaction Integrity")


    print("-----------------------------------")
    print("PHASE 3 - INTERVIEW ASSIGNMENT")
    print("-----------------------------------")
    future_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    assign_req = {
        "template_id": template_id,
        "candidate_id": cand_id,
        "scheduled_at": future_time
    }
    
    resp_assign = requests.post(f"{BASE_URL}/api/v1/admin/interviews/schedule", json=assign_req, headers=headers)
    assign_status = "PASS" if resp_assign.status_code == 201 else "FAIL"
    
    try:
        assign_json = resp_assign.json()
    except Exception:
        assign_json = resp_assign.text
    
    # Try fetching from API response first
    interview_id = assign_json.get("id") if isinstance(assign_json, dict) and resp_assign.status_code == 201 else None
    
    # Fallback: Query from DB directly if API failed but transaction was committed
    if not interview_id:
        db_fetch = asyncio.run(async_db_query("SELECT id FROM interviews WHERE candidate_id = :c_id", {"c_id": cand_id}))
        if db_fetch:
            interview_id = str(db_fetch[0][0])
            print("Recovered interview_id from DB:", interview_id)
    
    db_interviews = asyncio.run(async_db_query("SELECT status, candidate_id FROM interviews WHERE id = :id", {"id": interview_id})) if interview_id else []
    db_i_status = db_interviews[0][0] if db_interviews else None
    step_print("Schedule Interview", "POST /api/v1/admin/interviews/schedule", assign_req, resp_assign.status_code, assign_json, f"status={db_i_status}", assign_status, "Transaction Integrity")

    resp_sum = requests.get(f"{BASE_URL}/api/v1/admin/interviews/summary", headers=headers)
    sum_status = "PASS" if resp_sum.status_code == 200 and any(i["interview_id"] == interview_id for i in resp_sum.json().get("data", [])) else "FAIL"
    step_print("Get Interview Summary", "GET /api/v1/admin/interviews/summary", {}, resp_sum.status_code, "List of interviews", f"Includes {interview_id}", sum_status, "Transaction Integrity")

    if not interview_id:
        print("Stop! No interview_id")
        return

    print("-----------------------------------")
    print("PHASE 4 - CONCURRENCY TEST")
    print("-----------------------------------")
    
    headers_c = {"Authorization": f"Bearer {cand_token}"}
    
    def start_interview():
        return requests.post(f"{BASE_URL}/api/v1/candidate/interviews/{interview_id}/start", headers=headers_c)

    # Fire 2 concurrent starts
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(start_interview)
        f2 = executor.submit(start_interview)
        r1, r2 = f1.result(), f2.result()

    db_sessions = asyncio.run(async_db_query("SELECT id FROM interview_sessions WHERE interview_id = :iv_id", {"iv_id": interview_id}))
    session_count = len(db_sessions) if db_sessions else 0
    session_id = str(db_sessions[0][0]) if session_count > 0 else None
    
    conc_status = "PASS" if session_count == 1 and (r1.status_code == 200 or r2.status_code == 200) else "FAIL"
    step_print("Rapid concurrent starts", f"POST /api/v1/candidate/interviews/{interview_id}/start", {}, f"{r1.status_code}, {r2.status_code}", f"{r1.text[:20]}... {r2.text[:20]}...", f"Sessions: {session_count}", conc_status, "Concurrency Integrity")

    print("-----------------------------------")
    print("PHASE 6 - WEBSOCKET VALIDATION")
    print("-----------------------------------")
    ws_status = "FAIL"
    try:
        from websockets.sync.client import connect
        with connect("ws://127.0.0.1:8000/api/v1/proctoring/ws") as websocket:
            websocket.send(json.dumps({"type": "HANDSHAKE", "interview_id": session_id, "candidate_token": cand_token}))
            message = websocket.recv()
            msg = json.loads(message)
            if msg.get("type") == "HANDSHAKE_ACK":
                ws_status = "PASS"
    except Exception as e:
        print("WS error", e)
    
    step_print("Proctoring Handshake", "WS /api/v1/proctoring/ws", {"type": "HANDSHAKE..."}, "N/A", "ACK received" if ws_status == "PASS" else "FAIL", "N/A", ws_status, "WebSocket Integrity")

    print("-----------------------------------")
    print("PHASE 5 - ANSWER FLOW")
    print("-----------------------------------")
    headers_sess = {"Authorization": f"Bearer {cand_token}", "X-Interview-Id": session_id}
    requests.post(f"{BASE_URL}/api/v1/session/start", headers=headers_sess)
    
    answers = 0
    while True:
        nxt = requests.get(f"{BASE_URL}/api/v1/question/next", headers=headers_sess)
        if nxt.status_code != 200:
            break
        nxt_data = nxt.json()
        
        q_id = nxt_data.get("question_id")
        s_ans = requests.post(f"{BASE_URL}/api/v1/submit/submit", headers=headers_sess, json={"question_id": q_id, "answer": "Test answer", "transcript_id": str(uuid.uuid4()), "score": 8, "evaluation": "good"})
        answers += 1
        
    db_sess_info = asyncio.run(async_db_query("SELECT answered_count FROM interview_sessions WHERE id = :s_id", {"s_id": session_id}))
    answered_c = db_sess_info[0][0] if db_sess_info else 0
    
    ans_status = "PASS" if answered_c == 3 else "FAIL"
    step_print("Submit answers", "POST /api/v1/submit/submit", {"answer": "Test..."}, 200, "...", f"answered_count={answered_c}", ans_status, "Transaction Integrity")

    # Extra answer attempt
    extr = requests.post(f"{BASE_URL}/api/v1/submit/submit", headers=headers_sess, json={"question_id": str(uuid.uuid4()), "answer": "Extra"})
    extr_status = "PASS" if extr.status_code in [400, 404, 409, 403] else "FAIL"
    step_print("Extra answer after completion", "POST /api/v1/submit/submit", {}, extr.status_code, extr.json() if extr.text else "", "No extra row", extr_status, "Transaction Integrity")




    print("-----------------------------------")
    print("PHASE 7 - FINAL DATABASE STATE CHECK")
    print("-----------------------------------")
    
    i_state = asyncio.run(async_db_query("SELECT status FROM interviews WHERE id = :id", {"id": interview_id}))
    s_state = asyncio.run(async_db_query("SELECT status, answered_count FROM interview_sessions WHERE id = :id", {"id": session_id}))
    
    iv_s = i_state[0][0] if i_state else None
    sess_s = s_state[0][0] if s_state else None
    ans_c = s_state[0][1] if s_state else 0
    
    db_pass = "PASS" if iv_s == "COMPLETED" and sess_s == "completed" and ans_c == 3 else "FAIL"
    print(f"Validation: interview.status={iv_s} (Expected: COMPLETED)")
    print(f"Validation: interview_session.status={sess_s} (Expected: completed)")
    print(f"Validation: answered_count={ans_c} (Expected: 3)")
    step_print("Final states", "DB", "N/A", "N/A", "N/A", f"Interview={iv_s}, Session={sess_s}", db_pass, "Transaction Integrity")

    print("-----------------------------------")
    print("REPORT FORMAT REQUIRED")
    print("-----------------------------------")
    print(f"Overall System Health: {results['Overall System Health']}")
    print(f"Concurrency Integrity: {results['Concurrency Integrity']}")
    print(f"Transaction Integrity: {results['Transaction Integrity']}")
    print(f"Auth Integrity: {results['Auth Integrity']}")
    print(f"WebSocket Integrity: {results['WebSocket Integrity']}")

if __name__ == "__main__":
    run_tests()
