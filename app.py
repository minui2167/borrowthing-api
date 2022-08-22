from flask import Flask
from flask_restful import Api
from config import Config
from flask_jwt_extended import JWTManager
from resources.chat import ChatRoomResource
from resources.community import LoginStatusPostingInfoResources, LoginStatusPostingListResource, PostingCommentResource, PostingInfoResource, PostingLikesResource, PostingListResource, PostingCommentInfoResource
from resources.goods import GoodsCategoryResource, GoodsCommentResource, GoodsDealResource, GoodsInterestItemResource, GoodsPostingResource, GoodsRecommendResource, GoodsReviewResource, LoginStatusGoodsPostingResource
from resources.goods2 import GoodsListInAreaResource, GoodsListResource
from resources.users import UserActivityAreaResource, UserBuyResource, UserBuyingResource, UserCommunityCommentResource, UserEditResource, UserGoodsCommentResource, UserLikesPostingResource, UserLocationResource, UserLoginResource, UserLogoutResource, UserPurchaseCompleteResource, UserRegisterResource, UserSaleResource, UserWishlistResource, jwt_blacklist

app = Flask(__name__)

# 환경변수 셋팅
app.config.from_object(Config)

# JWT 토큰 라이브러리 만들기
jwt = JWTManager(app)

# 로그아웃 된 토큰이 들어있는 set을, jwt 에 알려준다.
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in jwt_blacklist

api = Api(app)

# users
api.add_resource(UserRegisterResource, '/users/register')
api.add_resource(UserLoginResource, '/users/login')
api.add_resource(UserLogoutResource, '/users/logout')
api.add_resource(UserEditResource, '/users/edit')
api.add_resource(UserLikesPostingResource, '/users/likes')
api.add_resource(UserWishlistResource, '/users/wishlist')
api.add_resource(UserBuyResource, '/users/buy')
api.add_resource(UserSaleResource, '/users/sale')
api.add_resource(UserLocationResource, '/users/location')
api.add_resource(UserCommunityCommentResource, '/users/community/comment')
api.add_resource(UserGoodsCommentResource, '/users/goods/comment')
api.add_resource(UserActivityAreaResource, '/users/location/distance')
api.add_resource(UserBuyingResource, '/users/goods/ing')
api.add_resource(UserPurchaseCompleteResource, '/users/goods/end')


# goods
api.add_resource(GoodsListResource, '/goods')
api.add_resource(GoodsListInAreaResource, '/goods/area')
api.add_resource(GoodsPostingResource, '/goods/<int:goodsId>')
api.add_resource(LoginStatusGoodsPostingResource, '/goods/login/<int:goodsId>')
api.add_resource(GoodsCommentResource, '/goods/<int:goodsId>/comment')
api.add_resource(GoodsCategoryResource, '/categories')
api.add_resource(GoodsReviewResource, '/evaluation/<int:goodsId>')
api.add_resource(GoodsInterestItemResource, '/goods/<int:goodsId>/wish')
api.add_resource(GoodsRecommendResource, '/goods/recommend')
api.add_resource(GoodsDealResource, '/goods/<int:goodsId>/deal')

# community
api.add_resource(PostingListResource, '/community')
api.add_resource(LoginStatusPostingListResource, '/community/login')
api.add_resource(PostingInfoResource, '/community/<int:postingId>')
api.add_resource(LoginStatusPostingInfoResources, '/community/login/<int:postingId>')
api.add_resource(PostingCommentResource,'/community/<int:postingId>/comment')
api.add_resource(PostingCommentInfoResource,'/community/<int:postingId>/comment/<int:commentId>')
api.add_resource(PostingLikesResource, '/community/<int:postingId>/likes')

# chat
api.add_resource(ChatRoomResource, '/community/<int:postingId>/likes')
if __name__ == '__main__' :
    app.run()