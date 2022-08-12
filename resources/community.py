from flask_restful import Resource
from flask_jwt_extended import get_jwt_identity, jwt_required

class PostingListResource(Resource) :
    # 커뮤니티 게시글 작성
    @jwt_required()
    def post(self) :
        pass

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
