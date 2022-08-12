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

        # photo(file), content(text)

        if 'photo1' not in request.files:
            return {'error' : '파일을 업로드하세요'}, 400

        # 2. S3에 파일 업로드
        # 클라이언트로부터 파일을 받아온다.
        file = request.files['photo1']
        content = request.form['content']

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
        pass

class PostingInfoResource(Resource) :
    # 커뮤니티 게시글 수정
    @jwt_required()
    def put(self) :
        pass

    # 커뮤니티 게시글 삭제
    @jwt_required()
    def delete(self) :
        pass

    # 특정 커뮤니티 게시글 가져오기
    def get(self) :
        pass

class PostingCommentResource(Resource) :
    # 커뮤니티 게시글 댓글 달기
    @jwt_required()
    def post(self) :
        pass

    # 커뮤니티 게시글 댓글 수정
    @jwt_required()
    def put(self) :
        pass

    # 커뮤니티 게시글 댓글 삭제
    @jwt_required()
    def delete(self) :
        pass

    # 커뮤니티 게시글 댓글 목록
    def get(self) :
        pass

class PostingLikesResource(Resource) :
    # 커뮤니티 게시글 좋아요 등록
    @jwt_required()
    def post(self) :
        pass

    # 커뮤니티 게시글 좋아요 해제
    @jwt_required()
    def delete(self) :
        pass

    # 커뮤니티 게시글 좋아요 누른 사람 목록
    def get(self) :
        pass
