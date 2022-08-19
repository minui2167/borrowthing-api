from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3
import requests
from config import Config

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
                    where sellerId = %s and id = %s;'''
            record = (userId, goodsId)
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
            

            # 태그 삭제하기
            query = '''Delete from tags
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
        
        # rekognition 을 이용해서 object detection 한다.
        client = boto3.client('rekognition',
                            'ap-northeast-2',                               # region
                            aws_access_key_id = Config.ACCESS_KEY,          # ACCESS_KEY   
                            aws_secret_access_key = Config.SECRET_ACCESS)   # SECRET_ACCESS

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
                    recode = (goodsId, imageId)

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

                response = client.detect_labels(Image = {
                                                'S3Object' : {
                                                        'Bucket' : Config.S3_BUCKET,
                                                        'Name' : file.filename
                                                        }},
                                        MaxLabels = 2)
                
                # 4. 레이블의 Name을 가지고, 태그를 만든다! 

                # 4-1. label['Name'] 의 문자열을 tag_name 테이블에서 찾는다.
                #      테이블에 이 태그가 있으면, id를 가져온다.
                #      태그 id와 위의 goodsId 를 가지고, 
                #      tags 테이블에 저장한다.

                # 4-2. 만약 tag_name 테이블에 이 태그가 없으면, 
                #      tag_name 테이블에, 이 태그 이름을 저장하고,
                #      저장된 id 값과 위의 goodsId를 가지고,
                #      tags 테이블에 저장한다.
        
                for label in response['Labels'] :
                    # label['Name'] 이 값을 우리는 태그 이름으로 사용할것
                    try :
                        # 파파고 번역하기
                        hearders = {'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Naver-Client-Id' : Config.NAVER_CLIENT_ID,
                            'X-Naver-Client-Secret' : Config.NAVER_CLIENT_SECRET}

                        data = {'source' : 'en',
                                'target' : 'ko',
                                'text' : label['Name']}

                        res = requests.post(Config.NAVER_PAPAGO_URL, data, headers = hearders)
                        
                        translatedText = res.json()['message']['result']['translatedText']
                        # 1. DB에 연결
                        connection = get_connection()
                        
                        # 2. 쿼리문 만들기
                        query = '''select * from tag_name
                                    where name = %s;'''                 

                        record = (translatedText,)
                        
                        # 3. 커서를 가져온다.
                        # select를 할 때는 dictionary = True로 설정한다.
                        cursor = connection.cursor(dictionary = True)

                        # 4. 쿼리문을 커서를 이용해서 실행한다.
                        cursor.execute(query, record)

                        # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
                        items = cursor.fetchall()

                        if len(items) == 0 :
                            # 태그 이름을 insert 해준다.
                            query = '''insert into tag_name
                                    (name)
                                    values
                                    (%s);'''
                            # recode 는 튜플 형태로 만든다.
                            recode = (translatedText, )

                            # 3. 커서를 가져온다.
                            cursor = connection.cursor()

                            # 4. 쿼리문을 커서를 이용해서 실행한다.
                            cursor.execute(query, recode)

                            # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
                            connection.commit()

                            # 태그 아이디를 가져온다.
                            tagNameId = cursor.lastrowid
                        else :
                            tagNameId = items[0]['id']
                        
                        # goodsId 와 tagNameId가 준비되었으니
                        # tag 테이블에 insert 한다.
                        query = '''insert into tags
                            (goodsId, tagNameId)
                            values
                            (%s, %s);'''   
                        # recode 는 튜플 형태로 만든다.
                        recode = (goodsId, tagNameId)

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
                        cursor.close()
                        connection.close()

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
                    where sellerId = %s and id = %s'''
            record = (userId, goodsId)
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

            # 태그 삭제
            query = '''Delete from tags
                    where goodsId = %s;'''
            record = (goodsId, )

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
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
    def get(self, goodsId) :
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            # 2. 쿼리문 만들기
            query = '''select g.id, g.sellerId, g.title, g.content, g.price, g.viewCount, 
                    g.status, g.rentalPeriod, g.createdAt, count(gi.imageId) as imgCount,
                    (select count(id) as attentionCount
                    from wish_lists
                    where goodsId = %s) as attentionCount,
                    (select count(id) as commentCount
                    from goods_comments
                    where goodsId = %s) as commentCount
                    from goods g
                    join goods_image gi
                        on g.id = gi.goodsId
                    group by g.id
                    having id = %s;'''            
            record = (goodsId, goodsId, goodsId)
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
                        from goods_image gi
                        join images i
                        on gi.imageId = i.id
                        where goodsId = %s;'''
            record = (goodsId, )
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

            
            # 태그 가져오기
            query = '''select tn.name tagName from tags t
                    join tag_name tn
                    on t.tagNameId = tn.id
                    where goodsId = %s;'''
            record = (goodsId, )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            itemTags = cursor.fetchall()
            if not itemTags:
                items[0]['Tag'] = []
            else :
                items[0]['Tag'] = itemTags


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

class GoodsCommentResource(Resource) :
    @jwt_required()
    # 빌려주기 글에 댓글 달기
    def post(self, goodsId) :
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
            query = '''insert into goods_comments
                    (goodsId, userId, comment)
                    values
                    (%s, %s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (goodsId, userId, data['comment'])

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

    @jwt_required()
    # 빌려주기 글에 댓글 삭제
    def delete(self, goodsId) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()

        # 게시물 작성
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from goods_comments
                    where userId = %s'''
            record = (userId, )
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :
                cursor.close()
                connection.close()
                return {'error' : '잘못된 접근입니다.'}
            
            # 2. 쿼리문 만들기
            query = '''delete from goods_comments
                    where userId = %s and goodsId = %s;'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, goodsId)

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

class GoodsReviewResource(Resource) :
     @jwt_required()
     # 거래 후기 작성
     def post(self, goodsId) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()
        data = request.get_json()
        

        # 리뷰 작성
        # 3. DB에 저장
        try :
            
            
            # DB에 연결
            connection = get_connection()
            
            # 조건 검사용 쿼리
            query = '''select status from goods
                    where id = %s'''
            
            record = (goodsId, )

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 거래 완료 상태인지 확인
            item = cursor.fetchall()
            if item[0]['status'] != 2 :
                return {"error" : "거래 완료 상태가 아닙니다."}, 200


            score = data['score']
            # 점수 범위 확인
            if score > 5 or score < 1 :
                return {"error" : "평가 점수를 제대로 입력해주세요."}, 200

            # insert 쿼리문 만들기
            query = '''insert into evaluation_items
                    (authorId, goodsId, score)
                    values
                    (%s, %s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, goodsId, score)

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

class GoodsInterestItemResource(Resource) :
     @jwt_required()
     # 관심 상품 등록
     def post(self, goodsId) :
        # 1. 클라이언트로부터 데이터를 받아온다.
        userId = get_jwt_identity()
        
        try :
            
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            
            query = '''select id, sellerId, status 
                    from goods
                    where id = %s ;'''
            
            record = (goodsId,)

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            item = cursor.fetchall()

            # 본인상품을 관심목록에 추가하는지 확인
            if item[0]['sellerId'] == userId :
                return {"error" : "본인 상품은 추가할 수 없습니다."}, 200

            # 거래대기 상태인지 확인
            if item[0]['status'] != 0 :
                return {"error" : "거래 대기 상태가 아닙니다."}, 200


            # 2. 쿼리문 만들기
            query = '''insert into wish_lists
                    (userId, goodsId)
                    values
                    (%s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, goodsId)

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


     @jwt_required()
     # 관심 상품 해제
     def delete(self, goodsId) :
        try :
            # 클라이언트로부터 데이터를 받아온다.
            userId = get_jwt_identity()

            # 데이터 Delete
            # 1. DB에 연결
            connection = get_connection()


            query = '''Delete from wish_lists
                        where userid = %s and goodsId = %s;'''                 
            record = (userId, goodsId)

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


class GoodsCategoryResource(Resource) :
     # 카테고리 목록 가져오기
     def get(self) :
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기         
            query = '''select * from categories
                        order by id;''' 

            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query,)

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


class GoodsRecommendResource(Resource) :
     @jwt_required()
     # 추천하는 빌려주기 글 가져오기
     def get(self) :
        pass

class GoodsDealResource(Resource) :
    @jwt_required()
    # 거래 신청하기
    def post(self) :
        # 상품의 거래상태가 0 (거래 대기)일 때, 거래신청이 가능
        # 거래 신청을 하면 buy 테이블에 상품, 구매자 추가
        # 상품의 상태를 1 (거래 중)로 변경
        userId = get_jwt_identity()
        data = request.get_json()
        print(data['goodsId'])
        try :
            # 1. DB에 연결
            connection = get_connection()   

            # 게시글 가져오기         
            query = '''select * from goods
                    where id = %s'''

            record = (data['goodsId'], )
            # 3. 커서를 가져온다.
            # select를 할 때는 dictionary = True로 설정한다.
            cursor = connection.cursor(dictionary = True)

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, record)

            # 5. select 문은, 아래 함수를 이용해서, 데이터를 받아온다.
            items = cursor.fetchall()
            
            # 판매자가 아닌지 확인
            if items[0]['sellerId'] == userId :
                return {"error" : "본인 글입니다."}, 200

            # 거래대기 상태 확인
            if items[0]['status'] != 0 :
                return {"error" : "거래 대기 상태가 아닙니다."}, 200


            # 거래 신청을 하면 buy 테이블에 상품, 구매자 추가
            # 2. 쿼리문 만들기
            query = '''insert into buy
                    (buyerId, goodsId)
                    values
                    (%s, %s);'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (userId, data['goodsId'])

            # 3. 커서를 가져온다.
            cursor = connection.cursor()

            # 4. 쿼리문을 커서를 이용해서 실행한다.
            cursor.execute(query, recode)


            # 상품의 상태를 1 (거래 중)로 변경
            query = '''Update goods
                    set status = 1
                    where id = %s;'''
                    
            # recode 는 튜플 형태로 만든다.
            recode = (data['goodsId'], )

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

    # 거래 취소하기
    def post(self) :
        pass

    # 거래 완료하기
    def delete(self) :
        pass