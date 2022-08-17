from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3

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
    def delete(self) :
        pass
    
    # 특정 빌려주기글 가져오기
    def get(self) :
        pass
    
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
