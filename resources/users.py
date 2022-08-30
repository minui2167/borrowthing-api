import datetime
from pkgutil import iter_modules
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

            query = '''select u.*, count(ei.goodsId) ratingCount
                    from users u
                    left join evaluation_items ei
                    on u.id = ei.authorId
                    where u.email = %s
                    group by u.id;'''

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
                'accessToken' : accessToken,
                'nickname' : user_info['nickname'], 
                'ratingCount' : user_info['ratingCount']}, 200

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

            # 우리지역이 설정되어 있는지 확인
            query = '''select * from activity_areas
                    where userId = %s;'''
            record = (userId, )
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            isSet = cursor.fetchall()

            # 시, 도 지역 찾기
            query = '''select * from sido_areas
                    where name = %s;'''
            record = (data['sidoName'], )
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()
            if not items :
                return {"error" : "지원하는 지역이 아닙니다."}, 400
            sidoId = items[0]['id']

            # 시, 군, 구 찾기
            query = '''select * from sigg_areas
                    where sidoAreaId = %s and name = %s;'''
            record = (sidoId, data['siggName'])
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if not items :
                return {"error" : "지원하는 지역이 아닙니다."}, 400
            siggId = items[0]['id']
            # 읍, 면, 동 찾기
            query = '''select * from emd_areas
                    where siggAreaId = %s and name = %s;'''
            record = (sidoId, data['emdName'])
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if not items :
                return {"error" : "지원하는 지역이 아닙니다."}, 400
            emdId = items[0]['id']

            

            # 설정된 것이 없으면 insert
            if len(isSet) < 1 :
                query = '''insert into activity_areas
                        (emdId, userId)
                        values
                        (%s, %s)'''
                
                record = (emdId, userId)
            else :
                query = '''update activity_areas
                        set emdId = %s
                        where userId = %s'''
            
                record = (emdId, userId)

            # 5-2. 커서를 가져온다.
            cursor = connection.cursor()

            # 5-3. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5-4. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503

        return {'result' : 'success'}, 200
    
    

    # 우리 동네 불러오기
    @jwt_required()
    def get(self):
        userId = get_jwt_identity()

        try :
            connection = get_connection()

            query = '''select aa.userId, aa.emdId, aa.activityMeters, sda.name sido, sga.name sigg, ea.name emd
                    from activity_areas aa
                    join emd_areas ea
                    on aa.emdId = ea.id
                    join sigg_areas sga
                    on ea.siggAreaId = sga.id
                    join sido_areas sda
                    on sga.sidoAreaId = sda.id
                    where userId = %s;'''
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()

            return {"error" : str(e), 'error_no' : 20}, 503

        return {'result' : 'success', 
                'items' : items}, 200

class UserWishlistResource(Resource) :
    @jwt_required()
    # 내 관심 상품 가져오기
    def get(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        try :
            connection = get_connection()

            query = '''select g.*, wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, wishes.isWish
                    from 
                    (select g.*, u.nickname from goods g
                    join users u
                    on g.sellerId = u.id) g,
                    (select g.id, count(wl.id) wishCount from goods g
                                            left join wish_lists wl
                                            on g.id = wl.goodsId
                                            group by g.id) wishCount,
                    (select g.id, count(gc.id) commentCount from goods g
                                            left join goods_comments gc
                                            on g.id = gc.goodsId
                                            group by g.id) commentCount,
                    (select g.id, count(gi.id) imgCount from goods g
                                            left join goods_image gi
                                            on g.id = gi.goodsId
                                            group by g.id) imgCount,    
                    (select g.*, if(wl.userId is null, 0, 1) isWish
                                            from goods g
                                            left join wish_lists wl
                                            on g.id = wl.goodsId and wl.userId = %s
                                            group by g.id) wishes
                    where g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id and g.id = wishes.id and isWish = 1
                    group by g.id
                    limit {}, {};'''.format(offset, limit)
            
            record = (userId, )

            # select 문은, dictionary = True 를 해준다.
            cursor = connection.cursor(dictionary = True)

            cursor.execute(query, record)

            # select 문은, 아래 함수를 이용해서, 데이터를 가져온다.
            items = cursor.fetchall()

            print(items)

            i=0
            
            selectedId = []
            cnt = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                items[i]['updatedAt'] = record['updatedAt'].isoformat()

                selectedId.append(record['id'])

                i = i+1
            
            itemImages = []
            itemTags = []
            
            for id in selectedId :
                # 게시글 사진 가져오기
                query = '''
                select i.imageUrl
                from images i
                join goods_image gi
                    on i.id = gi.imageId
                where gi.goodsId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)
                
                # 게시글 태그 가져오기
                query = '''select tn.name tagName from tags t
                        join tag_name tn
                        on t.tagNameId = tn.id
                        where goodsId = {};'''.format(id)
                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                tags = cursor.fetchall()
                itemTags.append(tags)
            i=0
            for record in items :
                items[i]['imgUrl'] = itemImages[i]
                items[i]['tag'] = itemTags[i]
                i += 1

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200

class UserLikesPostingResource(Resource) :
    @jwt_required()
    # 내가 좋아요 누른 게시물 가져오기
    def get(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        
        userId = get_jwt_identity()
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기         
            query = '''select p.* , likesCount.likesCount, commentCount.commentCount, imgCount.imgCount, likes.isLike
                        from 
                        (select p.*, u.nickname from posting p
                        join users u
                        on p.userId = u.id) p,
                        (select p.id, count(l.id) likesCount from posting p
                        left join likes l
                        on p.id = l.postingId
                        group by p.id) likesCount,
                        (select p.id, count(pc.id) commentCount from posting p
                        left join posting_comments pc
                        on p.id = pc.postingId
                        group by p.id) commentCount,
                        (select p.id, count(pi.id) imgCount from posting p
                        left join posting_image pi
                        on p.id = pi.postingId
                        group by p.id) imgCount,
                        (select p.*, if(l.userId is null, 0, 1) isLike
                        from posting p
                        left join likes l
                        on p.id = l.postingId and l.userId = %s
                        group by p.id) likes
                        where p.id = likesCount.id and p.id = commentCount.id and p.id = imgCount.id and p.id = likes.id and isLike = 1
                        group by p.id
                        limit {}, {};'''.format(offset, limit)

            record = (userId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0
            
            selectedId = []
            cnt = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()

                selectedId.append(record['id'])

                i = i+1
            
            itemImages = []
            # 게시글 사진 가져오기
            for id in selectedId :
                query = '''
                select i.imageUrl
                from posting_image pi
                join images i
                on pi.imageId = i.id
                where postingId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)

            
            
            i=0
            for record in items :
                items[i]['imgUrl'] = itemImages[i]
                i += 1 
            
            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200



class UserSaleResource(Resource) :
    @jwt_required()
    # 판매내역 가져오기
    def get(self) :
        userId = get_jwt_identity()

        offset = request.args.get('offset')
        limit = request.args.get('limit')   
        status = request.args.get('status') 
        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400

        if status is None or int(status) > 2 or int(status) < 0:
            return {'error' : 'status를 제대로 셋팅해 주세요.',
                    'error_no' : 123}, 400                    
        try :
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기
            # imageCount : 이미지 등록수, wishCount : 관심 등록 수, commentCount : 댓글 등록수
            if int(status) == 0 :
                query = '''select g.* , wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, if(g.sellerId = %s, 1, 0) isAuthor
                            from goods g,
                            (select g.id, count(wl.id) wishCount from goods g
                                                    left join wish_lists wl
                                                    on g.id = wl.goodsId
                                                    group by g.id) wishCount,
                            (select g.id, count(gc.id) commentCount from goods g
                                                    left join goods_comments gc
                                                    on g.id = gc.goodsId
                                                    group by g.id) commentCount,
                            (select g.id, count(gi.id) imgCount from goods g
                                                    left join goods_image gi
                                                    on g.id = gi.goodsId
                                                    group by g.id) imgCount
                            where g.sellerId = %s and g.status = {} and g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id 
                            order by g.updatedAt desc
                            limit {}, {};'''.format(status, offset, limit) 
            elif int(status) == 1 or int(status) == 2 :
                query = '''select g.* , wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, if(g.sellerId = %s, 1, 0) isAuthor
                            from 
                            (select g.*, b.buyerId, u.nickname from goods g
                                                    join buy b
                                                    on g.id = b.goodsId
                                                    join users u
                                                    on b.buyerId = u.id) g,
                            (select g.id, count(wl.id) wishCount from goods g
                                                    left join wish_lists wl
                                                    on g.id = wl.goodsId
                                                    group by g.id) wishCount,
                            (select g.id, count(gc.id) commentCount from goods g
                                                    left join goods_comments gc
                                                    on g.id = gc.goodsId
                                                    group by g.id) commentCount,
                            (select g.id, count(gi.id) imgCount from goods g
                                                    left join goods_image gi
                                                    on g.id = gi.goodsId
                                                    group by g.id) imgCount
                            where g.sellerId = %s and g.status = {} and g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id 
                            order by g.updatedAt desc
                            limit {}, {};'''.format(status, offset, limit)   
            else :
                return {"error" : "허용되지 않은 status 값 입니다."}, 400                                                    
            record = (userId, userId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0         
            selectedId = []
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                items[i]['updatedAt'] = record['updatedAt'].isoformat()
                selectedId.append(record['id'])
                i = i+1

            itemImages = []
            itemTags = []
            # 게시글 사진 가져오기
            for id in selectedId :
                query = '''
                select i.imageUrl
                from images i
                join goods_image gi
                    on i.id = gi.imageId
                where gi.goodsId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)


                query = '''select tn.name tagName from tags t
                        join tag_name tn
                        on t.tagNameId = tn.id
                        where goodsId = {};'''.format(id)
                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                tags = cursor.fetchall()
                itemTags.append(tags)
            i=0
            for record in items :
                items[i]['imgUrl'] = itemImages[i]
                items[i]['tag'] = itemTags[i]
                i += 1

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200
                
class UserGoodsCommentResource(Resource) :
    @jwt_required()
    # 내가 쓴 빌려주기 게시글 댓글 목록
    def get(self) :
        userId = get_jwt_identity()

        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 1. DB에 연결
            connection = get_connection()   

            # 댓글 가져오기         
            query = '''select gc.id commentId, gc.userId, gc.comment, gc.createdAt,
                    g.id postingId, g.sellerId authorId, g.content
                    from goods_comments gc
                    join goods g
                    on gc.goodsId = g.id
                    having gc.userId = %s
                    limit {}, {};'''.format(offset, limit) 
            
            record = (userId, )

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()

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
        
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200

class UserCommunityCommentResource(Resource) :
    @jwt_required()
    # 내가 쓴 커뮤니티 게시글 댓글 목록
    def get(self) :

        userId = get_jwt_identity()

        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 1. DB에 연결
            connection = get_connection()   

            # 댓글 가져오기         
            query = '''select pc.id commentsId, pc.userId, pc.comment, pc.createdAt,
                    p.id postingId, p.userId authorId, p.content
                    from posting_comments pc
                    join posting p
                    on pc.postingId = p.id
                    having pc.userId = %s
                    limit {}, {};'''.format(offset, limit) 
            
            record = (userId, )

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()

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
        
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200

class UserActivityAreaResource(Resource) :
    # 활동 범위 설정하기
    @jwt_required()
    def put(self) :

        userId = get_jwt_identity()
        data = request.get_json()

        # DB 업데이트 실행코드
        try :

            # 데이터 Update
            # 1. DB에 연결
            connection = get_connection()            
            

            # 2. 쿼리문 만들기
            query = '''Update activity_areas
                    set activityMeters = %s
                    where userId = %s;'''                 

            record = (data['activityMeters'], userId)

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
            return {"error" : str(e)}, 503

        return {'result' : 'success'}, 200

    # 활동 범위 내에 있는 동네 가져오기
    @jwt_required()
    def get(self) :
        userId = get_jwt_identity()
        
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기
            # imageCount : 이미지 등록수, wishCount : 관심 등록 수, commentCount : 댓글 등록수
            
            query = '''select emd.*, sigg.sidoAreaId from area_distances ad
                join activity_areas aa
                on ad.originArea = aa.emdId and aa.activityMeters >= ad.distance
                join emd_areas emd
                on ad.goalArea = emd.id
                join sigg_areas sigg
                on emd.siggAreaId = sigg.id
                join sido_areas sido
                on sigg.sidoAreaId = sido.id
                where aa.userId = %s;'''
                            
            record = (userId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200


class UserBuyResource(Resource) :
    # 구매내역 가져오기
    @jwt_required()
    def get(self) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   
        status = request.args.get('status')
        userId = get_jwt_identity()
        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기
            # imageCount : 이미지 등록수, wishCount : 관심 등록 수, commentCount : 댓글 등록수
            if int(status) == 1 :
                query = '''select g.* , wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, isWish.isWish
                        from (select g.*, u.nickname from goods g
												join users u
                                                on g.sellerId = u.id
                                                left join buy b
                                                on g.id = b.goodsId 
                                                where b.buyerId = %s and g.status = {}) g,
                        (select g.id, count(wl.id) wishCount from goods g
                                                left join wish_lists wl
                                                on g.id = wl.goodsId
                                                group by g.id) wishCount,
                        (select g.id, count(gc.id) commentCount from goods g
                                                left join goods_comments gc
                                                on g.id = gc.goodsId
                                                group by g.id) commentCount,
                        (select g.id, count(gi.id) imgCount from goods g
                                                left join goods_image gi
                                                on g.id = gi.goodsId
                                                group by g.id) imgCount,
                        (select g.*, if(wl.userId is null, 0, 1) isWish
                                                from goods g
                                                left join wish_lists wl
                                                on g.id = wl.goodsId and wl.userId = %s
                                                group by g.id) isWish                     
                        where g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id and g.id = isWish.id
                        limit {}, {};'''.format(status, offset, limit) 
            elif int(status) == 2 :
                query = '''select g.* , wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, isWish.isWish
                        from (select g.*, u.nickname, ei.authorId, ei.score from goods g
                                                join users u
                                                on g.sellerId = u.id
                                                left join buy b
                                                on g.id = b.goodsId 
                                                left join evaluation_items ei
                                                on g.id = ei.goodsId
                                                where b.buyerId = %s and g.status = {}) g,
                        (select g.id, count(wl.id) wishCount from goods g
                                                left join wish_lists wl
                                                on g.id = wl.goodsId
                                                group by g.id) wishCount,
                        (select g.id, count(gc.id) commentCount from goods g
                                                left join goods_comments gc
                                                on g.id = gc.goodsId
                                                group by g.id) commentCount,
                        (select g.id, count(gi.id) imgCount from goods g
                                                left join goods_image gi
                                                on g.id = gi.goodsId
                                                group by g.id) imgCount,
                        (select g.*, if(wl.userId is null, 0, 1) isWish
                                                from goods g
                                                left join wish_lists wl
                                                on g.id = wl.goodsId and wl.userId = %s
                                                group by g.id) isWish
                        where g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id and g.id = isWish.id
                        limit {}, {};'''.format(status, offset, limit)
                
            else :
                return {"error" : "허용되지 않은 status 값 입니다."}, 400                        
            record = (userId, userId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0         
            selectedId = []
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                items[i]['updatedAt'] = record['updatedAt'].isoformat()
                selectedId.append(record['id'])
                i = i+1

            itemImages = []
            itemTags = []
            # 게시글 사진 가져오기
            for id in selectedId :
                query = '''
                select i.imageUrl
                from images i
                join goods_image gi
                    on i.id = gi.imageId
                where gi.goodsId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)


                query = '''select tn.name tagName from tags t
                        join tag_name tn
                        on t.tagNameId = tn.id
                        where goodsId = {};'''.format(id)
                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                tags = cursor.fetchall()
                itemTags.append(tags)
            i=0
            for record in items :
                items[i]['imgUrl'] = itemImages[i]
                items[i]['tag'] = itemTags[i]
                i += 1

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200

class UserNotRatingBuyResource(Resource) :
    # 상품평 남기지 않은 구매내역 가져오기
    @jwt_required()
    def get(self) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   
        
        userId = get_jwt_identity()
        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기
            # imageCount : 이미지 등록수, wishCount : 관심 등록 수, commentCount : 댓글 등록수
            
            
            query = '''select g.* , wishCount.wishCount, commentCount.commentCount, imgCount.imgCount, isWish.isWish
                    from (select g.*, u.nickname, ei.authorId, ei.score from goods g
                                            join users u
                                            on g.sellerId = u.id
                                            left join buy b
                                            on g.id = b.goodsId 
                                            left join evaluation_items ei
                                            on g.id = ei.goodsId
                                            where b.buyerId = %s and g.status = 2) g,
                    (select g.id, count(wl.id) wishCount from goods g
                                            left join wish_lists wl
                                            on g.id = wl.goodsId
                                            group by g.id) wishCount,
                    (select g.id, count(gc.id) commentCount from goods g
                                            left join goods_comments gc
                                            on g.id = gc.goodsId
                                            group by g.id) commentCount,
                    (select g.id, count(gi.id) imgCount from goods g
                                            left join goods_image gi
                                            on g.id = gi.goodsId
                                            group by g.id) imgCount,
                    (select g.*, if(wl.userId is null, 0, 1) isWish
                                            from goods g
                                            left join wish_lists wl
                                            on g.id = wl.goodsId and wl.userId = %s
                                            group by g.id) isWish
                    where g.id = wishCount.id and g.id = commentCount.id and g.id = imgCount.id and g.id = isWish.id
                    limit {}, {};'''.format(offset, limit)
                
                                  
            record = (userId, userId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0         
            selectedId = []
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                items[i]['updatedAt'] = record['updatedAt'].isoformat()
                if not record['authorId'] :
                    selectedId.append(record['id'])    
                i = i+1
            
            selectedItems = [] 
            if selectedId :        
                i=0 
                for record in items :
                    print("record ID : {}".format(record['id']))                    
                    if record['id'] in selectedId :
                        selectedItems.append(record) 
                    i = i+1
                itemImages = []
                itemTags = []
                # 게시글 사진 가져오기
                for id in selectedId :
                    query = '''
                    select i.imageUrl
                    from images i
                    join goods_image gi
                        on i.id = gi.imageId
                    where gi.goodsId = {};'''.format(id)

                    # 3. 커서를 가져온다.
                    # select를 할 때는 dictionary = True로 설정한다.
                    cursor = connection.cursor(dictionary = True)

                    # 4. 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query,)

                    # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                    images = cursor.fetchall()
                    itemImages.append(images)


                    query = '''select tn.name tagName from tags t
                            join tag_name tn
                            on t.tagNameId = tn.id
                            where goodsId = {};'''.format(id)
                    # 3. 커서를 가져온다.
                    # select를 할 때는 dictionary = True로 설정한다.
                    cursor = connection.cursor(dictionary = True)

                    # 4. 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query,)

                    # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                    tags = cursor.fetchall()
                    itemTags.append(tags)
                i=0
                for record in selectedItems :
                    selectedItems[i]['imgUrl'] = itemImages[i]
                    selectedItems[i]['tag'] = itemTags[i]
                    i += 1

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(selectedItems),
            "items" : selectedItems}, 200


class UserCommunityListResource(Resource) :
    # 내가 쓴 커뮤니티 게시글 리스트
    @jwt_required()
    def get(self) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        
        userId = get_jwt_identity()
        try :
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기         
            query = '''select p.* , likesCount.likesCount, commentCount.commentCount, imgCount.imgCount, isLike.isLike
                        ,if(p.userId = %s, 1, 0) isAuthor
                        from 
                        (select p.*, u.nickname from posting p
                        join users u
                        on p.userId = u.id and p.userId = %s) p,
                        (select p.id, count(l.id) likesCount from posting p
                        left join likes l
                        on p.id = l.postingId
                        group by p.id) likesCount,
                        (select p.id, count(pc.id) commentCount from posting p
                        left join posting_comments pc
                        on p.id = pc.postingId
                        group by p.id) commentCount,
                        (select p.id, count(pi.id) imgCount from posting p
                        left join posting_image pi
                        on p.id = pi.postingId
                        group by p.id) imgCount,
                        (select p.*, if(l.userId is null, 0, 1) isLike
                        from posting p
                        left join likes l
                        on p.id = l.postingId and l.userId = %s
                        group by p.id) isLike
                        where p.id = likesCount.id and p.id = commentCount.id and p.id = imgCount.id and p.id = isLike.id
                        group by p.id
                        order by p.createdAt desc
                        limit {}, {};'''.format(offset, limit)

            record = (userId, userId, userId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0
            
            selectedId = []
            cnt = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()

                selectedId.append(record['id'])

                i = i+1
            
            itemImages = []
            # 게시글 사진 가져오기
            for id in selectedId :
                query = '''
                select i.imageUrl
                from posting_image pi
                join images i
                on pi.imageId = i.id
                where postingId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)

            
            
            i=0
            for record in items :
                items[i]['imgUrl'] = itemImages[i]
                i += 1 
            
            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
    
        return {
            "result" : "success",
            "count" : len(items),
            "items" : items}, 200
