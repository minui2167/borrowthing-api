from passlib.hash import pbkdf2_sha256

# 원문 비밀번호를, 암호화 하는 함수
# 암호화는 할 수 있지만 복호화는 안되는 hash 사용
# 단방향 암호화
# hash의 패턴을 파악하지 못하도록 salt(seed)를 설정하여 사용한다.
def hash_password(original_password) :
    salt = 'borrow*1141'
    password = original_password + salt
    password = pbkdf2_sha256.hash(password)
    return password

# 비밀번호가 맞는지 확인하는 함수
# True, False로 리턴한다.
def check_password(original_password, hashed_password) :
    salt = 'borrow*1141'
    check = pbkdf2_sha256.verify(original_password+salt, hashed_password)
    return check