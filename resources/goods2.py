from datetime import datetime
from flask_restful import Resource
from flask import request
from mysql_connection import get_connection
import mysql.connector
from flask_jwt_extended import get_jwt_identity, jwt_required
import boto3
import requests
from config import Config

# 태그기능 추가 !
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
            query = '''select g.id, g.categoriId, g.sellerId, imageCount.image, g.title, g.content, g.price, 
                        g.viewCount, g.status,
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
            goodsId = cursor.lastrowid

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
                        print(translatedText)
                        
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
                    
        return {"result" : "success"}, 200

class GoodsListInAreaResource(Resource) :
    @jwt_required()
    # 활동 범위 내에 있는 빌려주기 글 가져오기
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
            userId = get_jwt_identity()

            # 게시글 가져오기
            # imageCount : 이미지 등록수, attentionCount : 관심 등록 수, commentCount : 댓글 등록수
            query = '''select u.nickname, g.sellerId, g.title, g.content, g.price, g.status,
                    ad.originArea, ea.name, ad.goalArea, ad.distance, aa.activityMeters, 
                    aa.authenticatedAt, g.rentalPeriod, g.createdAt, i.imageUrl
                    from area_distances ad
                    left join emd_areas ea
                        on ea.id = ad.originArea
                    left join activity_areas aa
                        on ea.id = aa.emdId
                    left join users u
                        on u.id = aa.emdId
                    left join goods g
                        on u.id = g.sellerId
                    join goods_image gi
                        on g.id = gi.goodsId
                    left join images i
                        on i.id = gi.imageId
                    where ad.originArea = %s and ad.distance <= aa.activityMeters
                    group by g.id;
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
                items[i]['authenticatedAt'] = record['authenticatedAt'].isoformat()

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