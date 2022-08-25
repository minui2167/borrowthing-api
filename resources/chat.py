from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required

class ChatRoomResource(Resource) : 
    # 채팅방 생성하기
    @jwt_required()
    def post(self, goodsId) :
        userId = get_jwt_identity()

        # goodsId와 buyerId가 일치하는 채팅방이 있는지 확인
        # 게시물 작성
        # 3. DB에 저장
        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select * from chat_room
                    where buyerId = %s and goodsId = %s;'''
            record = (userId, goodsId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            if len(items) < 1 :           
                # 2. 쿼리문 만들기
                query = '''insert into chat_room
                        (goodsId, buyerId)
                        values
                        (%s, %s);'''
                        
                # recode 는 튜플 형태로 만든다.
                recode = (goodsId, userId)

                # 3. 커서를 가져온다.
                cursor = connection.cursor()

                # 4. 쿼리문을 커서를 이용해서 실행한다.
                cursor.execute(query, recode)

                # 5. 커넥션을 커밋해줘야 한다 => 디비에 영구적으로 반영하라는 뜻
                connection.commit()

                # 이 포스팅의 아이디 값을 가져온다.
                chatRoomId = cursor.lastrowid

                # 작성자와 게시글이 유효한지 확인한다.
                query = '''select * from chat_room
                        where id = %s;'''
                record = (chatRoomId, )
                cursor = connection.cursor(dictionary = True)
                cursor.execute(query, record)
                items = cursor.fetchall()

            # 6. 자원 해제
            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()

                i = i+1
            cursor.close()
            connection.close()


        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
        
        return {"result" : "succes",
                "items" : items}

class ChatRoomListResource(Resource) :
    # 내가 속한 채팅방 리스트 가져오기
    @jwt_required()
    def get(self) :
        userId = get_jwt_identity()

        try :
            # 데이터 insert
            # 1. DB에 연결
            connection = get_connection()
            

            # 작성자와 게시글이 유효한지 확인한다.
            query = '''select cr.*, g.title, g.sellerId from chat_room cr
                    join goods g
                    on cr.goodsId = g.id
                    where cr.buyerId = %s or g.sellerId = %s;'''
            record = (userId, userId)
            cursor = connection.cursor(dictionary = True)
            cursor.execute(query, record)
            items = cursor.fetchall()

            # 6. 자원 해제
            i = 0
            for record in items :
                items[i]['createdAt'] = record['createdAt'].isoformat()

                i = i+1
            cursor.close()
            connection.close()

        except mysql.connector.Error as e :
            print(e)
            cursor.close()
            connection.close()
            return {"error" : str(e)}, 503
        
        return {"result" : "succes",
                "items" : items}





class ChatResource(Resource) :
    # 내게 온 메시지 확인
    @jwt_required()
    def get(self) :
        pass
    
    # 메시지 보내기
    @jwt_required()
    def post(self) :
        pass