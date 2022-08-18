from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3

from config import Config

class GoodsListResource(Resource) :
    # 빌려주기 글 목록 리스트
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
            # imageCount : 이미지 등록수, attentionCount : 관심 등록 수, commentCount : 댓글 등록수
            query = '''select g.id, g.categoriId, g.sellerId, imageCount.image, g.title, g.content, g.price, g.status,
                        imageCount.imageCount, attentionCount.attentionCount, commentCount.commentCount, g.rentalPeriod, g.createdAt
                        from goods g,
                        (select g.id, count(gi.imageId) as imageCount, gi.imageId as image
                        from goods g
                        join goods_image gi
                            on g.id = goodsId
                        group by g.id) as imageCount,
                        (select g.id, count(w.goodsId) as attentionCount
                        from goods g
                        left join wish_lists w
                            on g.id = w.goodsId
                        group by g.id) as attentionCount,
                        (select g.id, count(gc.comment) as commentCount
                        from goods g
                        left join goods_comments gc
                            on g.id = gc.goodsId
                        group by g.id) as commentCount
                        where g.id = imageCount.id and g.id = attentionCount.id and g.id = commentCount.id
                        group by g.id
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

                selectedId.append(record['id'])

                i = i+1
            
            itemImages = []
            # 게시글 사진 가져오기
            for id in selectedId :
                query = '''
                select gi.goodsId, gi.imageId, i.imageUrl
                from images i
                join goods_image gi
                    on i.id = gi.imageId
                having gi.goodsId = {};'''.format(id)

                # 3. 커서를 가져온다.
                # select를 할 때는 dictionary = True로 설정한다.
                cursor = connection.cursor(dictionary = True)

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query,)

                # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                images = cursor.fetchall()
                itemImages.append(images)

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
            "items" : items,
            "itemImages" : itemImages}, 200

    @jwt_required()
    # 빌려주기 글 작성
    def post(self) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        title = request.form['title']
        content = request.form['content']
        price = request.form['price']
        rentalPeriod = request.form['rentalPeriod']
        categoriId = request.form['categoriId']

        # 게시물 작성
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''insert into goods
                    (title, content, price, rentalPeriod, categoriId, sellerId)
                    values
                    (%s, %s, %s, %s, %s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (title, content, price, rentalPeriod, categoriId, userId)

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
        photoList = ['image']
        for photo in photoList :
            if photo in request.files:
                # 2. S3에 파일 업로드
                # 클라이언트로부터 파일을 받아온다.
                file = request.files[photo]

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
                    query = '''insert into goods_image
                            (goodsId, imageId)
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

class GoodsPostingResource(Resource) :
    @jwt_required()
    # 빌려주기 글 수정
    def put(self, goodsId) :
        title = request.form['title']
        content = request.form['content']
        price = request.form['price']
        rentalPeriod = request.form['rentalPeriod']
        categoriId = request.form['categoriId']

        userId = get_jwt_identity()


        # DB 업데이트 실행코드
        try :

            # 데이터 Update
            # 1. DB에 연결
            connection = get_connection()            
            
            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from goods
                    where sellerId = %s;'''
            record = (userId, )
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}

            # 2. 쿼리문 만들기
            query = '''update goods
                    set title = %s, content = %s,
                    price = %s, rentalPeriod = %s, categoriId = %s
                    where id = %s;'''                 

            record = (title, content, price, rentalPeriod, categoriId, goodsId)

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 2. 이미지 삭제하기
            query = '''Delete from goods_image
                        where goodsId = %s;'''                 
            record = (goodsId, )

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
        photoList = ['photo1', 'photo2', 'photo3']
        for photo in photoList :
            if photo in request.files:
                # 2. S3에 파일 업로드
                # 클라이언트로부터 파일을 받아온다.
                file = request.files[photo]

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
                    query = '''insert into goods_image
                            (goodsId, imageId)
                            values
                            (%s, %s);'''
                            
                    # recode 는 튜플 형태로 만든다.
                    recode = (goodsId, imageId)

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

    @jwt_required()
    # 빌려주기 글 삭제
    def delete(self, goodsId) :
        try :
            # 클라이언트로부터 데이터를 받아온다.
            userId = get_jwt_identity()

            # 데이터 Delete
            # 1. DB에 연결
            connection = get_connection()

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from goods
                    where sellerId = %s'''
            record = (userId, )
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}
            
            # 2. 쿼리문 만들기

            # 관심 상품 삭제
            query = '''Delete from wish_lists
                    where goodsId = %s;'''                 
            record = (goodsId, )
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 구매하기 삭제
            query = '''Delete from buy
                    where goodsId = %s;'''                 
            record = (goodsId, )
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 이미지 삭제
            query = '''Delete from goods_image
                    where goodsId = %s;'''                 
            record = (goodsId, )
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 거래 후기 삭제
            query = '''Delete from evaluation_items
                    where goodsId = %s;'''                 
            record = (goodsId, )
            cursor = connection.cursor()
            cursor.execute(query, record)

            # 게시글 삭제
            query = '''Delete from goods
                        where id = %s and sellerId = %s;'''                 
            record = (goodsId, userId)

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
    
    # 특정 빌려주기글 가져오기
    def get(self) :
        pass

class GoodsCommentResource(Resource) :
    @jwt_required()
    # 빌려주기 글에 댓글 달기
    def post(self) :
        pass

    @jwt_required()
    # 빌려주기 글에 댓글 삭제
    def delete(self) :
        pass

class GoodsRecommendResource(Resource) :
     @jwt_required()
     # 추천하는 빌려주기 글 가져오기
     def get(self) :
        pass