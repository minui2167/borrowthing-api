from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3

from config import Config
  
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
