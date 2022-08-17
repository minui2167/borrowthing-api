import datetime
from flask import request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, get_jwt_identity
from flask_restful import Resource
from mysql_connection import get_connection
import mysql.connector

from email_validator import validate_email, EmailNotValidError

from utils import check_password, hash_password

class UserRegisterResource(Resource) :
    # 회원가입하기
    def post(self) :
        
    #    {
    #       "email" : "abc@naver.com",
    #       "password" : "1234",
    #       "name" : "홍길동",
    #       "phoneNumber" : "010-1234-1234",
    #       "nickname" : "홍길동"
    #     }

        # 1. 클라이언트가 body 에 보내준 json 을 받아온다.
        data = request.get_json()

        # 2. 이메일 주소형식이 제대로 된 주소형식인지
        # 확인하는 코드 작성.

        try :
            validate_email( data['email'] )
        except EmailNotValidError as e:
            # email is not valid, exception message is human-readable
            print(str(e))
            return {'error' : str(e)} , 400        
        
        # 3. 비밀번호의 길이가 유효한지 체크한다.
        # 비번길이는 4자리 이상, 12자리 이하로만!
        if len(data['password']) < 4 or len(data['password']) > 12 :
            return {'error' : '비밀번호 길이를 확인하세요'}, 400

        # 4. 비밀번호를 암호화 한다.
        hashedPassword = hash_password( data['password'] )

        print(hashedPassword)

        # 5. 데이터베이스에 회원정보를 저장한다!!
        try :
            # 데이터 insert 
            # 1. DB에 연결
            connection = get_connection()

            # 5-1. 쿼리문 만들기
            query = '''insert into users
                    (email, password, name, phoneNumber, nickname)
                    values
                    (%s, %s , %s, %s, %s);'''
            
            record = (data['email'], hashedPassword, data['name'],
            data['phoneNumber'], data['nickname'])

            # 5-2. 커서를 가져온다.
            cursor = connection.cursor()

            # 5-3. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5-4. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 5-5. 디비에 저장된 아이디값 가져오기.
            user_id = cursor.lastrowid

            # 6. 데이터 가져오기
            items = cursor.fetchall()

            # 6-1. 문자열로 바꿔서 다시 저장하기
            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503

        return {'result' : 'success'}, 200

class UserLoginResource(Resource) :
    # 로그인하기
    def post(self) :
        # 1. 클라이언트로부터 body로 넘어온 데이터를 받아온다.
        # {
        #     "email": "abc@naver.com",
        #     "password": "1234"
        # }

        data = request.get_json()

        # 2. 이메일로, DB에 이 이메일과 일치하는 데이터를
        # 가져온다.

        try :
            connection = get_connection()

            query = '''select *
                    from users
                    where email = %s;'''

            record = (data['email'] , )
            
            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            # 중요! 디비에서 가져온 timestamp 는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는! 이데이터를 json 으로 바로 보낼수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e)}, 400

        
        # 3. result_list 의 행의 갯수가 1개이면,
        # 유저 데이터를 정상적으로 받아온것이고
        # 행의 갯수가 0이면, 요청한 이메일은, 회원가입이
        # 되어 있지 않은 이메일이다.

        if len(items) != 1 :
            return {'error' : '등록되어 있지 않은 이메일입니다.'}, 400

        # 4. 비밀번호가 맞는지 확인한다.
        user_info = items[0]

        # data['password'] 와 user_info['password']를 비교

        check = check_password(data['password'] , user_info['password'])

        if check == False :
            return {'error' : '비밀번호가 맞지 않습니다.'}, 400

        accessToken = create_access_token( user_info['id'])

        return {'result' : 'success', 
                'accessToken' : accessToken}, 200

jwt_blacklist = set()
class UserLogoutResource(Resource) :
    @jwt_required()
    # 로그아웃하기
    def post(self) :

        jti = get_jwt()['jti']
        print(jti)
        
        jwt_blacklist.add(jti)

        return {'result' : 'success'}, 200

class UserEditResource(Resource) :
    @jwt_required()
    # 내 정보 수정하기
    def put(self) :
        
        data = request.get_json()
        userId = get_jwt_identity()

        hashedPassword = hash_password( data['password'] )

        # 2. 디비 업데이트
        try :
            # 데이터 업데이트 
            # 1. DB에 연결
            connection = get_connection()

            # 2. 쿼리문 만들기
            query = '''update users 
                    set nickname = %s, password = %s
                    where id = %s;'''
            
            record = (data["nickname"], hashedPassword, userId)

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 503

        return {'result' : 'success'}, 200

class UserLocationResource(Resource) :
    @jwt_required()
    # 우리 동네 설정하기
    def post(self) :
        data = request.get_json()
        userId = get_jwt_identity()

        try :
            # 데이터 insert 
            # 1. DB에 연결
            connection = get_connection()

            # 5-1. 쿼리문 만들기
            query = '''insert into activity_areas
                    (emdId, userId)
                    values
                    (%s, %s)'''
            
            record = (data["emdId"], userId)

            # 5-2. 커서를 가져온다.
            cursor = connection.cursor()

            # 5-3. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5-4. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 5-5. 디비에 저장된 아이디값 가져오기.
            userId = cursor.lastrowid

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503

        return {'result' : 'success'}, 200

class UserWishlistResource(Resource) :
    @jwt_required()
    # 내 관심 상품 가져오기
    def get(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select w.userId, w.goodsId, g.sellerId, g.createdAt, g.title, g.content, g.price, g.rentalPeriod, g.status
                    from goods g
                    join wish_lists w
                        on g.id = w.goodsId
                        where w.userId = %s;'''
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e), 'error_no' : 20}, 503

        return {'result' : 'success', 
                'count' : len(items),
                'items' : items}, 200

class UserLikesPostingResource(Resource) :
    @jwt_required()
    # 내가 좋아요 누른 게시물 가져오기
    def get(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select l.userId, l.postingId, p.content, 
                    p.viewCount, p.createdAt
                    from likes l
                    join posting p
                        on l.postingId = p.id
                    where l.userId = %s;'''
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            # 중요! 디비에서 가져온 timestamp 는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는! 이데이터를 json 으로 바로 보낼수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e), 'error_no' : 20}, 503

        return {'result' : 'success', 
                'count' : len(items),
                'items' : items}, 200

class UserBuyResource(Resource) :
    @jwt_required()
    # 구매내역 가져오기
    def get(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select u.nickname, g.categoriId, g.sellerId, g.createdAt, g.title, g.content, g.price, g.rentalPeriod, g.status, e.score
                    from users u
                    join goods g
                        on u.id = g.sellerId
                    join evaluation_items e
                        on g.id = e.goodsId
                    where u.id = %s and status != 2;'''
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e), 'error_no' : 20}, 503

        return {'result' : 'success', 
                'count' : len(items),
                'items' : items}, 200

class UserSaleResource(Resource) :
    @jwt_required()
    # 판매내역 가져오기
    def get(self) :
        userId = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select u.nickname, g.categoriId, g.sellerId, g.createdAt, g.title, g.content, g.price, g.rentalPeriod, g.status
                    from users u
                    join goods g
                        on u.id = g.sellerId
                    where u.id = %s and status = 2;
                    '''
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i + 1

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e), 'error_no' : 20}, 503

        return {'result' : 'success', 
                'count' : len(items),
                'items' : items}, 200