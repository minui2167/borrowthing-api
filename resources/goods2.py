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
     def post(self) :
        pass

class GoodsInterestItemResource(Resource) :
     @jwt_required()
     # 관심 상품 등록
     def post(self) :
        pass

     @jwt_required()
     # 관심 상품 해제
     def delete(self) :
        pass


class GoodsCategoryResource(Resource) :
     @jwt_required()
     # 카테고리 목록 가져오기
     def get(self) :
        pass
