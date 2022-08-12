import datetime
from flask import request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, get_jwt_identity
from flask_restful import Resource
from mysql_connection import get_connection
import mysql.connector

from email_validator import validate_email, EmailNotValidError

from utils import check_password, hash_password

class GoodsListResource(Resource) :
    # 빌려주기 글 목록 리스트
    def get(self) :
        pass

class GoodsWriteResource(Resource) :
     @jwt_required()
     # 빌려주기 글 작성
     def post(self) :
        pass

class GoodsUpdateResource(Resource) :
     @jwt_required()
     # 빌려주기 글 수정
     def put(self) :
        pass

class GoodsDeleteResource(Resource) :
     @jwt_required()
     # 빌려주기 글 삭제
     def delete(self) :
        pass

class GoodsCommentResource(Resource) :
     @jwt_required()
     # 빌려주기 글에 댓글 달기
     def post(self) :
        pass

class GoodsCommentDeleteResource(Resource) :
     @jwt_required()
     # 빌려주기 글에 댓글 삭제
     def delete(self) :
        pass

class GoodsReviewResource(Resource) :
     @jwt_required()
     # 거래 후기 작성
     def post(self) :
        pass

class GoodsInterestItemResource(Resource) :
    @jwt_required()
    # 관심 상품 등록
    def post(self) :
        pass

class GoodsInterestItemDeleteResource(Resource) :
    @jwt_required()
    # 관심 상품 등록 해제
    def delete(self) :
        pass

class GoodsRecommendPostingResource(Resource) :
    @jwt_required()
    # 추천하는 빌려주기 글 가져오기
    def get(self) :
        pass

class GoodsCategoryResource(Resource) :
    # 카테고리 목록 가져오기
    def get(self) :
        pass

class GoodsSpecificPostingResource(Resource) :
    # 특정 빌려주기 글 가져오기
    def get(self) :
        pass