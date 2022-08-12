from flask_restful import Resource
from flask_jwt_extended import get_jwt_identity, jwt_required

class ChatRoomResource(Resource) :
    # 내가 속한 채팅방 가져오기
    @jwt_required()
    def get(self):
        pass


class ChatResource(Resource) :
    # 내게 온 메시지 확인
    @jwt_required()
    def get(self) :
        pass
    
    # 메시지 보내기
    @jwt_required()
    def post(self) :
        pass