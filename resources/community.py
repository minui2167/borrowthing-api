from asyncio.windows_events import NULL
from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3

from config import Config

class PostingListResource(Resource) :
    # 커뮤니티 게시글 작성
    @jwt_required()
    def post(self) :

        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        content = request.form['content']

        # 게시물 작성
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''insert into posting
                    (userId, content)
                    values
                    (%s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, content)

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, recode)

            # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 이 포스팅의 아이디 값을 가져온다.
            postingId = cursor.lastrowid

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
            

        # photo(file), content(text)
        # photoList = ['photo1', 'photo2', 'photo3']
        # for photo in photoList :
        if 'photo' in request.files:
            # 2. S3에 파일 업로드
            # 클라이언트로부터 파일을 받아온다.
            files = request.files.getlist("photo")
            for file in files :
                # 파일명을 우리가 변경해 준다.
                # 파일명은, 유니크하게 만들어야 한다.
                current_time = datetime.now()
                new_file_name = current_time.isoformat().replace(':', '_') + ('.jpg')

                # 유저가 올린 파일의 이름을 내가 만든 파일명으로 변경
                file.filename = new_file_name
                print(file.filename)
                # S3에 업로드 하면 된다.
                # AWS의 라이브러리를 사용해야 한다.
                # 이 파이썬 라이브러리가 boto3 라이브러리다.
                # pip install boto3
                s3 = boto3.client('s3', 
                            aws_access_key_id = Config.ACCESS_KEY,
                            aws_secret_access_key = Config.SECRET_ACCESS)

                try :
                    s3.upload_fileobj(file,             # 업로드 파일
                                    Config.S3_BUCKET,   # 버킷 url
                                    file.filename,      # 파일명
                                    ExtraArgs = {'ACL' : 'public-read', 'ContentType' : file.content_type})    # 권한, 타입

                except Exception as e:
                    return {'error' : str(e)}, 500       

                # 사진을 DB에 저장
                try :
                    # 데이터 insert
                    # 1. DB에 연결
                    connection = get_connection()
                    
                    # 2. 쿼리문 만들기
                    query = '''insert into images
                            (userId, imageUrl)
                            values
                            (%s, %s);'''
                            
                    # recode 는 튜플 형태로 만든다.
                    recode = (userId, file.filename)

                    # 3. 커서를 가져온다.
                    cursor = connection.cursor()

                    # 4. 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query, recode)

                    # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
                    connection.commit()

                    # 이 포스팅의 아이디 값을 가져온다.
                    imageId = cursor.lastrowid

                    # 6. 자원 해제
                    cursor.close()
                    connection.close()

                except mysql.connector.Error as e :
                    print(e)
                    cursor.close()
                    connection.close()
                    return {"error" : str(e)}, 503
                
                # 게시글 사진 id로 저장하기
                try :
                    # 데이터 insert
                    # 1. DB에 연결
                    connection = get_connection()
                    
                    # 2. 쿼리문 만들기
                    query = '''insert into posting_image
                            (postingId, imageId)
                            values
                            (%s, %s);'''
                            
                    # recode 는 튜플 형태로 만든다.
                    recode = (postingId, imageId)

                    # 3. 커서를 가져온다.
                    cursor = connection.cursor()

                    # 4. 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query, recode)

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
            
        return {"result" : "success"}, 200

    # 커뮤니티 게시글 목록 리스트
    def get(self) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기         
            query = '''select p.* , likesCount.likesCount, commentCount.commentCount, imgCount.imgCount
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
                        group by p.id) imgCount
                        where p.id = likesCount.id and p.id = commentCount.id and p.id = imgCount.id
                        group by p.id
                        order by p.createdAt desc
                        limit {}, {};'''.format(offset, limit)

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,)

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

                # if record['imgCount'] > 0 :
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

    
class LoginStatusPostingListResource(Resource) :
    # 로그인 상태일 때 게시글 목록 리스트 (isLike 추가))
    @jwt_required()
    def get(self) :
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
            query = '''select p.* , likesCount.likesCount, commentCount.commentCount, imgCount.imgCount, isLike.isLike
                        ,if(p.userId = %s, 1, 0) isAuthor
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
                        group by p.id) isLike
                        where p.id = likesCount.id and p.id = commentCount.id and p.id = imgCount.id and p.id = isLike.id
                        group by p.id
                        order by p.createdAt desc
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
        
  
class PostingInfoResource(Resource) :
    # 커뮤니티 게시글 수정
    @jwt_required()
    def put(self, postingId) :
        content = request.form['content']

        userId = get_jwt_identity()


        # DB 업데이트 실행코드
        try :

            # 데이터 Update
            # 1. DB에 연결
            connection = get_connection()            
            
            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from posting
                    where userId = %s and id = %s;'''
            record = (userId, postingId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}

            # 2. 쿼리문 만들기
            query = '''Update posting
                    set content = %s
                    where id = %s and userId = %s;'''                 

            record = (content, postingId, userId)

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 2. 이미지 삭제하기
            query = '''Delete from posting_image
                        where postingId = %s;'''                 
            record = (postingId, )

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
        
        # 이미지 다시 추가
        # photo(file), content(text)
        if 'photo' in request.files:
            # 2. S3에 파일 업로드
            # 클라이언트로부터 파일을 받아온다.
            files = request.files.getlist("photo")
            for file in files :
                # 파일명을 우리가 변경해 준다.
                # 파일명은, 유니크하게 만들어야 한다.
                current_time = datetime.now()
                new_file_name = current_time.isoformat().replace(':', '_') + ('.jpg')

                # 유저가 올린 파일의 이름을 내가 만든 파일명으로 변경
                file.filename = new_file_name
                print(file.filename)
                # S3에 업로드 하면 된다.
                # AWS의 라이브러리를 사용해야 한다.
                # 이 파이썬 라이브러리가 boto3 라이브러리다.
                # pip install boto3
                s3 = boto3.client('s3', 
                            aws_access_key_id = Config.ACCESS_KEY,
                            aws_secret_access_key = Config.SECRET_ACCESS)

                try :
                    s3.upload_fileobj(file,             # 업로드 파일
                                    Config.S3_BUCKET,   # 버킷 url
                                    file.filename,      # 파일명
                                    ExtraArgs = {'ACL' : 'public-read', 'ContentType' : file.content_type})    # 권한, 타입

                except Exception as e:
                    return {'error' : str(e)}, 500       

                # 사진을 DB에 저장
                try :
                    # 데이터 insert
                    # DB에 연결
                    connection = get_connection()
                    
                    # 쿼리문 만들기
                    # 사진을 DB에 저장
                    query = '''insert into images
                            (userId, imageUrl)
                            values
                            (%s, %s);'''
                            
                    # recode 는 튜플 형태로 만든다.
                    recode = (userId, file.filename)

                    # 커서를 가져온다.
                    cursor = connection.cursor()

                    # 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query, recode)

                    # 이 포스팅의 아이디 값을 가져온다.
                    imageId = cursor.lastrowid


                    # 게시글 사진 id로 저장하기
                    query = '''insert into posting_image
                            (postingId, imageId)
                            values
                            (%s, %s);'''
                            
                    # recode 는 튜플 형태로 만든다.
                    recode = (postingId, imageId)

                    # 커서를 가져온다.
                    cursor = connection.cursor()

                    # 쿼리문을 커서를 이용해서 실행한다.
                    cursor.execute(query, recode)

                    # 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
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

    # 커뮤니티 게시글 삭제
    @jwt_required()
    def delete(self, postingId) :
        try :
            # 클라이언트로부터 데이터를 받아온다.
            userId = get_jwt_identity()

            # 데이터 Delete
            # 1. DB에 연결
            connection = get_connection()

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from posting
                    where userId = %s and id = %s;'''
            record = (userId, postingId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}
            
            # 2. 쿼리문 만들기
            # 이미지 삭제
            query = '''Delete from posting_image
                    where postingId = %s;'''                 
            record = (postingId,)
            cursor = connection.cursor()
            cursor.execute(query, record)

            # likes 삭제
            query = '''Delete from likes
                    where postingId = %s;'''                 
            record = (postingId,)
            cursor = connection.cursor()
            cursor.execute(query, record)

            # comments 삭제
            query = '''Delete from posting_comments
                    where postingId = %s;'''                 
            record = (postingId,)
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 게시글 삭제
            query = '''Delete from posting
                        where id = %s and userId = %s;'''                 
            record = (postingId, userId)

            cursor = connection.cursor()
            cursor.execute(query, record)

        

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

    # 특정 커뮤니티 게시글 가져오기
    def get(self, postingId) :
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''select p.* , count(pi.imageId) imgCount,
                    (select count(id) commentCount
                                    from posting_comments
                                    where postingId = %s) commentCount,
                    (select count(id) likesCount
                                    from likes
                                    where postingId = %s) likesCount
                    from (select p.*, u.nickname from posting p
                        join users u
                        on p.userId = u.id) p
                    left join posting_image pi
                    on p.id = pi.postingId
                    group by p.id
                    having id = %s;'''            
            record = (postingId, postingId, postingId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0
            
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()             
                i = i+1

            # 이미지 가져오기
            query = '''select i.imageUrl
                        from posting_image pi
                        join images i
                        on pi.imageId = i.id
                        where postingId = %s;'''
            record = (postingId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            itemImages = cursor.fetchall()
            

            if not itemImages:
                items[0]['imgUrl'] = []
            else :
                items[0]['imgUrl'] = itemImages


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

class LoginStatusPostingInfoResource(Resource) :
    # 로그인 상태일 때 특정 커뮤니티 게시글 가져오기
    @jwt_required()
    def get(self, postingId) :
        try :
            userId = get_jwt_identity()
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''select p.* , count(pi.imageId) imgCount,
                    (select count(id) commentCount
                                    from posting_comments
                                    where postingId = %s) commentCount,
                    (select count(id) likesCount
                                    from likes
                                    where postingId = %s) likesCount,
                    (select if(l.userId is null, 0, 1) isLike
                                    from posting p
                                    left join likes l
                                    on p.id = l.postingId and l.userId = %s
                                    where p.id = %s
                    ) isLike,
                    if(p.userId = %s, 1, 0) isAuthor
                    from 
                    (select p.*, u.nickname from posting p
                    join users u
                    on p.userId = u.id) p
                    left join posting_image pi
                    on p.id = pi.postingId
                    group by p.id
                    having p.id = %s;'''            
            record = (postingId, postingId, userId, postingId, userId, postingId)
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 중요! 디비에서 가져온 timestamp는 
            # 파이썬의 datetime 으로 자동 변경된다.
            # 문제는 이 데이터를 json으로 바로 보낼 수 없으므로,
            # 문자열로 바꿔서 다시 저장해서 보낸다.
            i=0
            
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()             
                i = i+1

            # 이미지 가져오기
            query = '''select i.imageUrl
                        from posting_image pi
                        join images i
                        on pi.imageId = i.id
                        where postingId = %s;'''
            record = (postingId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            itemImages = cursor.fetchall()
            print(itemImages)

            if not itemImages:
                items[0]['imgUrl'] = []
            else :
                items[0]['imgUrl'] = itemImages


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
        
class PostingCommentResource(Resource) :
    # 커뮤니티 게시글 댓글 달기
    @jwt_required()
    def post(self, postingId) :

        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        data = request.get_json()

        # 게시물 작성
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''insert into posting_comments
                    (postingId, userId, comment)
                    values
                    ({}, %s, %s);'''.format(postingId)
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, data['comment'])

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, recode)

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
            
        return {"result" : "success"}, 200

    # 커뮤니티 게시글 댓글 목록
    def get(self, postingId) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 댓글 가져오기         
            query = '''select pc.*, u.nickname from posting_comments pc
                    join users u
                    on pc.userId = u.id
                    where postingId = %s
                    limit {}, {};'''.format(offset, limit) 
            
            record = (postingId, )

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
            
        
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i+1      


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

class LoginStatusPostingCommentResource(Resource) :
    # 로그인 상태일 때 커뮤니티 게시글 댓글 목록
    @jwt_required()
    def get(self, postingId) :
        userId = get_jwt_identity()
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 댓글 가져오기         
            query = '''select pc.*, u.nickname, if(userId = %s, 1, 0) isAuthor
                    from posting_comments pc
                    join users u
                    on pc.userId = u.id
                    where postingId = %s
                    limit {}, {};'''.format(offset, limit) 
            
            record = (userId, postingId)

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
            
        
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()
                i = i+1      


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

class PostingCommentInfoResource(Resource) :
    # 커뮤니티 게시글 댓글 수정
    @jwt_required()
    def put(self, postingId, commentId) :

        userId = get_jwt_identity()
        data = request.get_json()


        # DB 업데이트 실행코드
        try :

            # 데이터 Update
            # 1. DB에 연결
            connection = get_connection()            
            
            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from posting_comments
                    where userId = %s and postingId = %s;'''
            record = (userId, postingId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}

            # 2. 쿼리문 만들기
            query = '''Update posting_comments
                    set comment = %s
                    where id = {} and userId = %s;'''.format(commentId)                 

            record = (data['comment'], userId)

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
        
        return {"result" : "success"}, 200

    # 커뮤니티 게시글 댓글 삭제
    @jwt_required()
    def delete(self, postingId, commentId) :
        try :
            # 클라이언트로부터 데이터를 받아온다.
            userId = get_jwt_identity()

            # 데이터 Delete
            # 1. DB에 연결
            connection = get_connection()

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from posting_comments
                    where userId = %s and id = %s and postingId = %s ;'''
            record = (userId, commentId, postingId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}

            # 게시글 삭제
            query = '''Delete from posting_comments
                        where id = %s and userId = %s;'''                 
            record = (commentId, userId)

            cursor = connection.cursor()
            cursor.execute(query, record)

        

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

    

class PostingLikesResource(Resource) :
    # 커뮤니티 게시글 좋아요 등록
    @jwt_required()
    def post(self, postingId) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()


        # 좋아요 등록
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''insert into likes
                    (userId, postingId)
                    values
                    (%s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, postingId)

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, recode)

            # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 2. 쿼리문 만들기
            query = '''select count(*) likesCount from likes
                    where postingId = %s
                    group by postingId;'''            
            record = (postingId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            likesCount = 0
            if items :
                likesCount = items[0]["likesCount"]

            

            # 6. 자원 해제
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
        
        return {"result" : "success",
                "likesCount" : likesCount}, 200

    # 커뮤니티 게시글 좋아요 해제
    @jwt_required()
    def delete(self, postingId) :
        try :
            # 클라이언트로부터 데이터를 받아온다.
            userId = get_jwt_identity()

            # 데이터 Delete
            # 1. DB에 연결
            connection = get_connection()


            # 좋아요 해제
            query = '''Delete from likes
                        where userId = %s and postingId = %s;'''                 
            record = (userId, postingId)

            cursor = connection.cursor()
            cursor.execute(query, record)


            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)


            # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
            connection.commit()

            # 2. 쿼리문 만들기
            query = '''select count(*) likesCount from likes
                    where postingId = %s
                    group by postingId;'''            
            record = (postingId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            likesCount = 0
            if items :
                likesCount = items[0]["likesCount"]

            # 6. 자원 해제
            cursor.close()
            connection.close()
        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503

        return {"result" : "success",
                "likesCount" : likesCount}, 200

    # 커뮤니티 게시글 좋아요 누른 사람 목록
    def get(self, postingId) :
        offset = request.args.get('offset')
        limit = request.args.get('limit')   

        if offset is None or limit is None :
            return {'error' : '쿼리스트링 셋팅해 주세요.',
                    'error_no' : 123}, 400
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 댓글 가져오기         
            query = '''select * from likes
                    where postingId = %s
                    limit {}, {};'''.format(offset, limit) 
            
            record = (postingId, )

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
