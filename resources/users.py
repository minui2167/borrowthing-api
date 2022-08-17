class UserGoodsCommentResource(Resource) :
    @jwt_required()
    # 내가 쓴 빌려주기 게시글 댓글 목록
    def get(self) :
        pass

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
                    p.id postingId, p.id sellerId, p.content
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