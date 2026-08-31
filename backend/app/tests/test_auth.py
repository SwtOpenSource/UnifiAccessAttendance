from app.auth import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_long_password_does_not_crash():
    # bcrypt 本身限制 72 bytes；改用直接呼叫 bcrypt（不透過已停止維護、
    # 跟新版 bcrypt 套件不相容的 passlib）之後，超長密碼要能正常截斷雜湊，
    # 不能像 passlib 1.7.4 + bcrypt 5.x 那樣直接丟 ValueError 炸掉建帳號流程。
    long_pw = "x" * 200
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed)
