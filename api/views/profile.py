""" API views responsible for returing and updating the profile info"""
import os
import uuid
import web
import math
from datetime import datetime

from api.utils import api_response, save_api_request, api_response, \
    photo_id_to_url
from api.views.base import BaseAPI
from api.views.social import share, get_comments_to_photo
from api.entities import UserProfile

from mypinnings import auth
from mypinnings import session
from mypinnings.database import connect_db
from mypinnings.conf import settings
from mypinnings.media import store_image_from_filename

from api.models.user import User
from api.models.album import Album
from api.models.picture import Picture


db = connect_db()


class BaseUserProfile(BaseAPI):
    """
    General class which holds list of fields used by user profile methods
    """
    def __init__(self):
        self._fields = ['id', 'name', 'about', 'city', 'country', 'hometown',
                        'about', 'email', 'pic_id', 'bg_id', 'website', 'facebook',
                        'twitter', 'getlist_privacy_level', 'private',
                        'bgx', 'bgy', 'show_views', 'views', 'username', 'zip',
                        'linkedin', 'gplus', 'headerbgy', 'headerbgx']
        self._birthday_fields = ['birthday_year', 'birthday_month',
                                 'birthday_day']
        self.required = ['csid_from_client', 'logintoken']
        self.default_fields = ['project_id', 'os_type', 'version_id','format_type']

    @staticmethod
    def format_birthday(user, response):
        """
        Composes birthday response, returning year, day and month
        as separate response fields
        """
        if user['birthday']:
            response['birthday_year'] = user['birthday'].year
            response['birthday_day'] = user['birthday'].day
            response['birthday_month'] = user['birthday'].month
        return response

    def is_request_valid(self, request_data):
        """
        Checks if all required parameters are sent from the client.
        Also checks if no extra arguments was passed
        """
        for field in self.required:
            if field not in request_data:
                return False

        for field in request_data:
            # Checking if current field is among the fields we have in the db
            if (field not in self._fields and
                    field not in self._birthday_fields and
                    field not in self.required and
                    field not in self.default_fields):
                return False
        return True


class SetPrivacy(BaseUserProfile):
    """
    Allows to set privacy level of the profile.

    :link: /api/profile/userinfo/update
    """
    def POST(self):
        """ Updates profile with fields sent from the client,
        returns saved fields.

        :param str csid_from_client: csid from client key
        :param str getlist_privacy_level/private: controls privacy level
        :param str logintoken: logintoken
        :response_data: Returns api response with 'getlist_privacy_level/private.'
        :to test: curl --data "logintoken=UaNxct7bJZ&twitter=1&csid_from_client=1" http://localhost:8080/api/profile/userinfo/update
        """
        request_data = web.input()

        # Adding field to the list of required fields
        # self.required.append('getlist_privacy_level')

        if not self.is_request_valid(request_data):
            return api_response(data={}, status=405,
                                error_code="Required args are missing")

        csid_from_client = request_data.pop('csid_from_client')

        data = {}

        privacy_level = request_data.get('getlist_privacy_level')
        private = request_data.get('private')

        if privacy_level:
            data['getlist_privacy_level'] = privacy_level
        if private:
            data['private'] = private

        status, response_or_user = self.authenticate_by_token(
            request_data.pop('logintoken'))
        # Login was not successful
        if not status:
            return response_or_user

        if len(data) > 0:
            db.update('users', where='id = %s' % (response_or_user['id']),
                      **data)

        csid_from_server = response_or_user['seriesid']
        return api_response(data=data,
                            csid_from_client=csid_from_client,
                            csid_from_server=csid_from_server)


class UserInfoUpdate(BaseUserProfile):
    """
    Defines a class responsible for updating user data, inside the profile

    :link: /api/profile/userinfo/update
    """
    def POST(self):
        """  Updates profile with fields sent from the client,
        returns saved fields.

        :param str csid_from_client: Csid string from client
        :param str logintoken: Logintoken
        :param str <field>: The field which will be changed
        :response_data: returns changed field
        :to test: curl --data "logintoken=UaNxct7bJZ&twitter=1&csid_from_client=1" http://localhost:8080/api/profile/userinfo/update

        """
        request_data = web.input()

        if not self.is_request_valid(request_data):
            return api_response(data={}, status=405,
                                error_code="Required args are missing")
        csid_from_client = request_data.pop('csid_from_client')

        status, response_or_user = self.authenticate_by_token(
            request_data.pop('logintoken'))
        # Login was not successful
        if not status:
            return response_or_user
        to_insert = {}

        birthday = [value for key, value in request_data.items()
                    if key in self._birthday_fields]

        if len(birthday) in [1, 2]:
            error_code = "Birthday date incomplete"
            return api_response(data={}, status=405, error_code=error_code)
        elif len(birthday) == 3:
            to_insert['birthday'] = datetime.strptime("-".join(birthday),
                                                      "%Y-%d-%m")
        for field in self._fields:
            item = request_data.get(field)
            if item:
                to_insert[field] = item

        if len(to_insert) > 0:
            db.update('users', where='id = %s' % (response_or_user['id']),
                      **to_insert)
        csid_from_server = response_or_user['seriesid']
        return api_response(data=request_data,
                            csid_from_client=csid_from_client,
                            csid_from_server=csid_from_server)


class GetProfileInfo(BaseUserProfile):
    """ Allows to render profile information, by token

    :url: /api/profile/userinfo/get
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: Logintoken

        :response_data: 'id', 'name', 'about', 'city', 'country','hometown', 'about', 'email', 'pic', 'website', 'facebook', 'twitter', 'getlist_privacy_level', 'private', 'bg', 'bgx', 'bgy', 'show_views', 'views', 'username', 'zip', 'linkedin', 'gplus', 'bg_resized_url', 'headerbgy', 'headerbgx'
        :to test: curl --data "logintoken=UaNxct7bJZ&csid_from_client=123" http://localhost:8080/api/profile/userinfo/get
        """
        request_data = web.input()
        if not self.is_request_valid(request_data):
            return api_response(data={}, status=405,
                                error_code="Required args are missing")
        status, response_or_user = self.authenticate_by_token(
            request_data.pop('logintoken'))

        # User id contains error code
        if not status:
            return response_or_user

        response = {field: response_or_user[field] for field in self._fields}
        response['resized_url'] = photo_id_to_url(response['pic_id'])
        response['bg_resized_url'] = photo_id_to_url(response['bg_id'])
        csid_from_client = request_data.pop('csid_from_client')
        csid_from_server = response_or_user['seriesid']
        self.format_birthday(response_or_user, response)
        return api_response(data=response,
                            csid_from_client=csid_from_client,
                            csid_from_server=csid_from_server)


class ProfileInfo(BaseUserProfile):
    """
    Returns public profile information

    :url: /api/profile/userinfo/info
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: Logintoken
        :param str username: Username
        :param str username: id
        :response_data: 'id', 'name', 'about', 'city', 'country','hometown', 'about', 'email', 'pic', 'website', 'facebook', 'twitter', 'getlist_privacy_level', 'private', 'bg', 'bgx', 'bgy', 'show_views', 'views', 'username', 'zip', 'linkedin', 'gplus', 'bg_resized_url', 'headerbgy', 'headerbgx'

        :to test:
        - curl --data "csid_from_client=11&id=78&logintoken=RxPu7fLYgv" http://localhost:8080/api/profile/userinfo/info
        - curl --data "csid_from_client=11&username=Oleg&logintoken=RxPu7fLYgv" http://localhost:8080/api/profile/userinfo/info
        """
        request_data = web.input()
        profile = request_data.get("username", "")
        user_id = request_data.get("id", 0)
        logintoken = request_data.get("logintoken", "")

        if not self.is_request_valid(request_data):
            return api_response(data={}, status=405,
                                error_code="Required args are missing")

        if not profile and not user_id:
            error_code = "This function requires either profile or user_id"
            return api_response(data={}, status=405,
                                error_code=error_code)

        status, response_or_user = self.authenticate_by_token(logintoken)
        if not status:
            return api_response(data={}, status=405,
                                error_code="You need to log in first")

        user = UserProfile.query_user(profile=profile, user_id=user_id)
        if not user:
            return api_response(data={}, status=405,
                                error_code="User was not found")
        followers = UserProfile\
            .query_followed_by(profile_owner=user.id,
                               current_user=response_or_user["id"])
        user.follower_count = len(followers)

        follow = UserProfile\
            .query_following(profile_owner=user.id,
                             current_user=response_or_user["id"])
        user.follow_count = len(follow)

        csid_from_client = request_data.pop('csid_from_client')
        csid_from_server = ""

        return api_response(data=user.to_serializable_dict(),
                            csid_from_client=csid_from_client,
                            csid_from_server=csid_from_server)

    def get_user_info(self, profile="", user_id=0):
        query = db.select('users',
                          vars={'username': profile, 'id': user_id},
                          where="username=$username or id=$id")

        if len(query) > 0:
            user = query.list()[0]
            user['pic'] = photo_id_to_url(user['pic'])
        else:
            return False
        response = {field: user[field] for field in self._fields}
        response = self.format_birthday(user, response)
        return response

class UpdateProfileViews(BaseUserProfile):
    """
    Responsible for updating count of pofile views

    :link: /api/profile/updateviews/<username>
    """
    def POST(self, profile):
        """
        :param str csid_from_client: Csid string from client
        :param str profile: must be in url
        :response_data: returns a dict with 'status' key
        :to test: curl --data "csid_from_client=11&logintoken=RxPu7fLYgv" http://localhost:8080/api/profile/updateviews/oleg
        """
        request_data = web.input()

        if not self.is_request_valid(request_data):
            return api_response(data={}, status=405,
                                error_code="Required args are missing")

        # Checking if user has a valid logintoken
        status, response_or_user = self.authenticate_by_token(
            request_data.pop('logintoken'))
        # Login was not successful
        if not status:
            return response_or_user

        db.update('users', where='user = $username',
                  vars={'username': profile},
                  views=web.SQLLiteral('views + 1'))

        csid_from_client = request_data.pop('csid_from_client')
        csid_from_server = ""

        return api_response(data={"status": "success"},
                            csid_from_client=csid_from_client,
                            csid_from_server=csid_from_server)


class ManageGetList(BaseAPI):
    """
    :link: /api/profile/mgl
    """
    def POST(self):
        """
        Manage list of user products: sharing, add, remove

        Method for image_id_share_list must additional receive next
        :param str csid_from_client: Csid string from client
        :param str logintoken: Logintoken
        :param str social_network: e.g. facebook
        :response_data: returns added/removed/shared getlists
        """
        request_data = web.input(
            image_id_remove_list=[],
            image_id_share_list=[],
            image_id_add_list=[],
        )

        # Setting default status code as 200
        status = 200
        # Setting empty error
        error_code = ""

        save_api_request(request_data)
        login_token = request_data.get("logintoken")

        status_success, response_or_user = self.authenticate_by_token(login_token)
        if not status_success:
            return response_or_user

        csid_from_client = request_data.get('csid_from_client')

        access_token = request_data.get("access_token")
        social_network = request_data.get("social_network")

        image_id_add_list = map(int, request_data.get("image_id_add_list"))
        add_list_result = []
        if len(image_id_add_list) > 0:
            add_list_result = self.add(response_or_user["id"],
                                       image_id_add_list)

        image_id_remove_list = map(int,
                                   request_data.get("image_id_remove_list"))
        remove_list_result = []
        if len(image_id_remove_list) > 0:
            remove_list_result = self.remove(response_or_user["id"],
                                             image_id_remove_list)

        image_id_share_list = map(int, request_data.get("image_id_share_list"))
        share_list_result = []
        if len(image_id_share_list) > 0:
            # Check input social data for posting
            if not access_token or not social_network:
                status = 400
                error_code = "Invalid input data"
            else:
                share_list_result, status, error_code = self.sharing(access_token, social_network,
                                                                 image_id_share_list)

        csid_from_server = response_or_user.get('seriesid')

        data = {
            "added": add_list_result,
            "removed": remove_list_result,
            "shared": share_list_result,
        }
        response = api_response(data,
                                status=status,
                                error_code=error_code,
                                csid_from_client=csid_from_client,
                                csid_from_server=csid_from_server)
        return response

    def add(self, user_id, add_list):
        """
        Add new products to user profile
        """
        add_list_result = []
        for pin in add_list:
            user_product = {"user_id": user_id, "pin_id": pin}
            exist_product = db.select(
                'user_prefered_pins',
                where=web.db.sqlwhere(user_product)
            )
            if len(exist_product) == 0:
                add_list_result.append(pin)
                db.insert('user_prefered_pins', user_id=user_id, pin_id=pin)
        return add_list_result

    def remove(self, user_id, remove_list):
        """
        Remove products from user profile
        """
        remove_list_result = []
        for pin in remove_list:
            user_product = {"user_id": user_id, "pin_id": pin}
            exist_product = db.select(
                'user_prefered_pins',
                where=web.db.sqlwhere(user_product)
            )
            if len(exist_product) > 0:
                remove_list_result.append(pin)
                db.delete(
                    'user_prefered_pins',
                    where=web.db.sqlwhere(user_product)
                )
        return remove_list_result

    def sharing(self, access_token, social_network, share_list):
        """
        Share products from user profile
        """

        share_list_result, status, error_code = share(access_token,
                                                      share_list,
                                                      social_network)

        return share_list_result, status, error_code


class ChangePassword(BaseAPI):
    """
    :link: /api/profile/pwd
    """
    def POST(self):
        """ Change user password and get/store new logintoken
        :param str csid_from_client: Csid string from client
        :param str logintoken: Logintoken
        :param str old_password: current password of the user
        :param str new_password, new_password2: The new password typed 2 times

        :response_data: new clinet token
        :to test:
        """
        request_data = web.input()
        save_api_request(request_data)
        client_token = request_data.get("logintoken")
        status, response_or_user = self.authenticate_by_token(client_token)
        if not status:
            return response_or_user

        old_password = request_data.get("old_password")
        new_password = request_data.get("new_password")
        new_password2 = request_data.get("new_password2")

        pw_salt = response_or_user['pw_salt']
        pw_hash = response_or_user['pw_hash']

        status, error = self.passwords_validation(pw_salt, pw_hash,
                                                  old_password, new_password,
                                                  new_password2,
                                                  response_or_user["username"],
                                                  response_or_user["email"])
        if status:
            new_password_hash = self.create_password(pw_salt, new_password)
            db.update('users', pw_hash=new_password_hash,
                      vars={'id': response_or_user["id"]}, where="id=$id")

            # re_login user with new password
            sess = session.get_session()
            auth.login_user(sess, response_or_user["id"])

            user = db.select('users', {'id': response_or_user["id"]},
                             where='id=$id')[0]
            new_client_token = user.get('logintoken')
            csid_from_server = user.get('seriesid')
            csid_from_client = request_data.get("csid_from_client")
            data = {
                "client_token": new_client_token,
            }
            response = api_response(data, csid_from_client,
                                    csid_from_server=csid_from_server)
        else:
            data = {}
            user = db.select('users', {'id': response_or_user["id"]},
                             where='id=$id')[0]
            csid_from_server = user.get('seriesid')
            csid_from_client = request_data.get("csid_from_client")

            response = api_response(data=data,
                                    status=400,
                                    error_code=error,
                                    csid_from_client=csid_from_client,
                                    csid_from_server=csid_from_server)

        return response

    def passwords_validation(self, pw_salt, pw_hash, old_pwd=None,
                             new_pwd=None, new_pwd2=None, uname=None,
                             email=None):
        """
        Check if new password match with confirmation.
        Check relevance old password.
        Check empty field.
        """
        if new_pwd is None:
            return False, self.access_denied("New password is empty")

        if old_pwd is None:
            return False, self.access_denied("Old password is empty")

        if new_pwd != new_pwd2:
            return False, self.access_denied("Passwords do not match")

        if str(hash(str(hash(old_pwd)) + pw_salt)) != pw_hash:
            return False, self.access_denied("Incorrect old password")

        pwd_status, error_code = auth.check_password(uname, new_pwd, email)
        if not pwd_status:
            return False, error_code

        return True, "Success"

    def create_password(self, pw_salt, new_pwd):
        new_pwd_hash = str(hash(new_pwd))
        new_pwd_hash = str(hash(new_pwd_hash + pw_salt))
        return new_pwd_hash


class QueryBoards(BaseAPI):
    """
    Class responsible for getting boards of a given user

    :link: /api/profile/userinfo/boards
    """
    def POST(self):
        """ Returns all boards associated with a given user

        :param str csid_from_client: Csid string from client
        :param str user_id: id of the queried user
        :param str current_user_id: id of current user
        :response_data: returns all boards of a given user as a list
        :to test: curl --data "user_id=2&csid_from_client=1" http://localhost:8080/api/profile/userinfo/boards
        """
        request_data = web.input()
        csid_from_client = request_data.get('csid_from_client')
        csid_from_server = ""
        current_user_id = request_data.get('current_user_id', 0)
        user_id = request_data.get('user_id')

        if not user_id:
            return api_response(data={}, status=405,
                                error_code="Missing user_id")
        boards_query = """
        SELECT b.id, b.name, b.description, bf.follower_id is not null
        as is_following FROM boards b
        LEFT JOIN boards_followers bf on bf.board_id = b.id
        and bf.follower_id = $cid WHERE b.user_id=$uid;
        """
        boards_tmp = db.query(boards_query,
                              vars={'uid': user_id, 'cid': current_user_id})

        boards = []
        for board in boards_tmp:
            pins_from_board = db.select('pins',
                               where='board_id=$board_id',
                               vars={'board_id': board['id']})
            board['pins_ids'] = []
            for pin_from_board in pins_from_board:
                if pin_from_board['id'] not in board['pins_ids']:
                    board['pins_ids'].append(pin_from_board['id'])
            boards.append(board)
        return api_response(data=boards,
                            csid_from_server=csid_from_server,
                            csid_from_client=csid_from_client)


class QueryPins(BaseAPI):
    """
    Responsible for getting pins of a given user

    :url: /api/profile/userinfo/pins
    """
    def POST(self):
        """ Returns all pins associated with a given user

        :param str csid_from_client: Csid string from client
        :param str user_id: id of the queried user
        :response_data: Returns list of pins of a current user

        :to test: curl --data "user_id=78&csid_from_client=1" http://localhost:8080/api/profile/userinfo/pins
        """
        query = '''
        select tags.tags, pins.*, users.pic_id as user_pic,
        users.username as user_username, users.name as user_name,
        count(distinct p1) as repin_count,
        count(distinct l1) as like_count
        from users
        left join pins on pins.user_id = users.id
        left join tags on tags.pin_id = pins.id
        left join pins p1 on p1.repin = pins.id
        left join likes l1 on l1.pin_id = pins.id
        where users.id = $id
        group by tags.tags, pins.id, users.id
        order by timestamp desc'''

        request_data = web.input()
        csid_from_client = request_data.get('csid_from_client')
        csid_from_server = ""
        user_id = request_data.get('user_id')

        if not user_id:
            return api_response(data={}, status=405,
                                error_code="Missing user_id")
        results = db.query(query, vars={'id': user_id})

        pins = []
        current_row = None
        pins_counter = len(results)
        owned_pins_counter = 0
        for row in results:
            if not row.id:
                continue
            if not current_row or current_row.id != row.id:
                current_row = row
                tag = row.tags
                current_row.tags = []
                if tag:
                    current_row.tags.append(tag)

                current_row_dt = datetime.fromtimestamp(current_row.timestamp)

                pins.append(current_row)
                if not current_row.get("repin"):
                    owned_pins_counter += 1
            else:
                tag = row.tags
                if tag not in current_row.tags:
                    current_row.tags.append(tag)

        data = {
            "total": pins_counter,
            "total_owned": owned_pins_counter
        }
        page = int(request_data.get("page", 1))
        if page is not None:
            items_per_page = int(request_data.get("items_per_page", 10))
            if items_per_page < 1:
                items_per_page = 1

            data['pages_count'] = math.ceil(float(len(pins)) /
                                            float(items_per_page))
            data['pages_count'] = int(data['pages_count'])
            data['page'] = page
            data['items_per_page'] = items_per_page

            start = (page-1) * items_per_page
            end = start + items_per_page
            data['pins_list'] = pins[start:end]
        else:
            data['pins_list'] = pins

        return api_response(data=data,
                            csid_from_server=csid_from_server,
                            csid_from_client=csid_from_client)

class TestUsernameOrEmail(BaseAPI):
    """
    Checks if given username or email is already added to database.
    in case if a username

    :link: /api/profile/test-username
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: username_or_email
        :response data: returns 'ok' or 'notfound'
        :to test: curl --data "csid_from_client=1&username_or_email=oleg" http://localhost:8080/api/profile/test-username
        """
        request_data = web.input()
        username_or_email = request_data.get('username_or_email')

        vars={'username_or_email': username_or_email}
        # Trying to find a user with same username
        result = db.select('users', vars=vars,
                           where='username=$username_or_email')
        # Fallback, trying to find user with same email
        if len(result.list()) == 0:
            result = db.select('users', vars=vars,
                               where='email=$username_or_email')

        if len(result.list()) == 0:
            status = 'notfound'
        else:
            status = 'ok'

        csid_from_client = request_data.get('csid_from_client')
        csid_from_server = ""
        return api_response(data=status,
                            csid_from_server=csid_from_server,
                            csid_from_client=csid_from_client)


class PicUpload(BaseAPI):
    """
    Upload profile picture and save it in database

    :link: /api/profile/userinfo/upload_pic
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: logintoken of user
        :param file file: file for saving
        :response data: returns id, original_url, resized_url of saved picture
        :to test: curl -F "csid_from_client=1" -F "logintoken=AmWG6AhgPO" -F "file=@/image/for/test.jpg" http://localhost:8080/api/profile/userinfo/upload_pic
        """
        data = {}
        status = 200
        csid_from_server = None
        error_code = ""

        request_data = web.input(file={})
        logintoken = request_data.get('logintoken')

        user_status, user = self.authenticate_by_token(logintoken)
        # User id contains error code
        if not user_status:
            return user

        csid_from_server = user['seriesid']
        csid_from_client = request_data.get("csid_from_client")

        file_obj = request_data.get('file')

        # For some reason, FileStorage object treats itself as False
        if type(file_obj) == dict:
            return api_response(data={}, status=405,
                                error_code="Required args are missing")

        album = self._get_or_create_album(user['id'], 'photos')

        photo = self._save_in_database(file_obj, 160, album.id)

        user_to_update = web.ctx.orm.query(User)\
            .filter(User.id == user['id'])\
            .first()

        user_to_update.pic_obj = photo
        web.ctx.orm.commit()

        data['id'] = photo.id
        data['original_url'] = photo.original_url
        data['resized_url'] = photo.resized_url

        response = api_response(data=data,
                                status=status,
                                error_code=error_code,
                                csid_from_client=csid_from_client,
                                csid_from_server=csid_from_server)

        return response

    def _get_or_create_album(self, user_id, slug):
        album = web.ctx.orm.query(Album).filter(Album.user_id == user_id,
                                               Album.slug == slug).first()

        if not album:
            album = Album(user_id, slug)

            web.ctx.orm.add(album)
            web.ctx.orm.commit()

        return album

    def _save_in_database(self, file_obj, resized_size, album_id):
        file_path = self._save_file(file_obj)
        enlarged = Image.open(file_path).size[0] * 0.3

        images_dict = store_image_from_filename(db,
                                                file_path,
                                                widths=[resized_size, enlarged])
        picture = Picture(
            album_id=album_id,
            original_url=images_dict[0]['url'],
            resized_url=images_dict.get(resized_size, images_dict[0])\
                .get('url', None),
            enlarged_url=images_dict.get(resized_size, images_dict[enlarged]).get('url', None)
        )

        web.ctx.orm.add(picture)
        web.ctx.orm.commit()

        return picture

    def _save_file(self, file_obj, upload_dir=None):
        """
        Saves uploaded file to a given upload dir.
        """
        if not upload_dir:
            upload_dir = self._get_media_path()
        filename = file_obj.filename
        filename = self._get_file_name(filename, upload_dir)
        filepath = os.path.join(upload_dir, filename)
        upload_file = open(filepath, 'w')
        upload_file.write(file_obj.file.read())
        upload_file.close()
        return filepath

    def _get_media_path(self):
        """
        Returns or creates media directory.
        """
        media_path = settings.MEDIA_PATH
        if not os.path.exists(media_path):
            os.makedirs(media_path)
        return media_path

    def _get_file_name(self, filename, upload_dir):
        """
        Method responsible for avoiding duplicated filenames.
        """
        filepath = os.path.join(upload_dir, filename)
        exists = os.path.isfile(filepath)
        # Suggest uuid hex as a filename to avoid duplicates
        if exists:
            filename = "%s.%s" % (uuid.uuid4().hex[:10], filename)
        return filename


class BgUpload(PicUpload):
    """
    Upload profile background and save it in database

    :link: /api/profile/userinfo/upload_bg
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: logintoken of user
        :param file file: file for saving
        :response data: returns id, original_url, resized_url of saved picture
        :to test: curl -F "csid_from_client=1" -F "logintoken=AmWG6AhgPO" -F "file=@/image/for/test.jpg" http://localhost:8080/api/profile/userinfo/upload_bg
        """
        data = {}
        status = 200
        csid_from_server = None
        error_code = ""

        request_data = web.input(file={})
        logintoken = request_data.get('logintoken')

        user_status, user = self.authenticate_by_token(logintoken)
        # User id contains error code
        if not user_status:
            return user

        csid_from_server = user['seriesid']
        csid_from_client = request_data.get("csid_from_client")

        file_obj = request_data.get('file')

        # For some reason, FileStorage object treats itself as False
        if type(file_obj) == dict:
            return api_response(data={}, status=405,
                                error_code="Required args are missing")

        album = self._get_or_create_album(user['id'], 'backgrounds')
        photo = self._save_in_database(file_obj, 1100, album.id)

        user_to_update = web.ctx.orm.query(User)\
            .filter(User.id == user['id'])\
            .first()

        user_to_update.bg = photo
        web.ctx.orm.commit()

        data['id'] = photo.id
        data['original_url'] = photo.original_url
        data['resized_url'] = photo.resized_url

        response = api_response(data=data,
                                status=status,
                                error_code=error_code,
                                csid_from_client=csid_from_client,
                                csid_from_server=csid_from_server)

        return response


class GetPictures(BaseAPI):
    """
    API method for get photos of user

    :link: /api/profile/userinfo/get_pictures
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: logintoken of user (is not required)
        :param int user_id: id of user
        :param str album_type: type of pictures (photos|backgrounds)
        :response data: returns photos - list of pictures
        :to test: curl --data "csid_from_client=1&user_id=93&album_type=photos" http://localhost:8080/api/profile/userinfo/get_pictures
        """
        request_data = web.input()

        update_data = {}
        data = {}
        status = 200
        csid_from_server = None
        error_code = ""

        # Get data from request
        user_id = request_data.get("user_id")
        album_type = request_data.get("album_type")

        csid_from_client = request_data.get('csid_from_client')

        current_user_id = None
        logintoken = request_data.get('logintoken', None)
        if logintoken:
            user_status, user = self.authenticate_by_token(logintoken)
            if user_status:
                current_user_id = user['id']


        album = web.ctx.orm.query(Album).filter(
            Album.user_id == user_id,
            Album.slug == album_type
        ).first()

        data['photos'] = []

        if album:
            pictures = web.ctx.orm.query(Picture).filter(
                Picture.album_id == album.id
            ).all()

            for picture in pictures:
                if not picture.resized_url:
                    continue

                picture = picture.to_serializable_dict()

                picture['likes_count'] = len(picture['likes'])

                if current_user_id:
                    for like in picture['likes']:
                        if like['user_id'] == current_user_id:
                            picture['liked'] = True
                            break
                else:
                    picture['liked'] = False

                data['photos'].append(picture)

        response = api_response(data=data,
                                status=status,
                                error_code=error_code,
                                csid_from_client=csid_from_client,
                                csid_from_server=csid_from_server)
        return response


class PictureRemove(BaseAPI):
    """
    Remove picture and save changes in database

    :link: /api/profile/userinfo/remove_pic
    """
    def POST(self):
        """
        :param str csid_from_client: Csid string from client
        :param str logintoken: logintoken of user
        :param int picture_id: id of photo that you wish to remove
        :response data: no extra rsponse
        :to test: curl --data "csid_from_client=1&picture_id=5&logintoken=XXXXXXX" http://localhost:8080/api/profile/userinfo/remove_pic
        """
        data = {}
        status = 200
        csid_from_server = None
        error_code = ""

        request_data = web.input()
        logintoken = request_data.get('logintoken')
        picture_id = request_data.get('picture_id')

        user_status, user = self.authenticate_by_token(logintoken)
        # User id contains error code
        if not user_status:
            return user

        csid_from_server = user['seriesid']
        csid_from_client = request_data.get("csid_from_client")

        self._delete_picture(user['id'], picture_id)

        response = api_response(data=data,
                                status=status,
                                error_code=error_code,
                                csid_from_client=csid_from_client,
                                csid_from_server=csid_from_server)

        return response

    def _delete_picture(self, user_id, picture_id):
        user_to_update = web.ctx.orm.query(User)\
            .filter(User.id == user_id)\
            .first()

        picture = web.ctx.orm.query(Picture)\
            .filter(Picture.id == picture_id)\
            .first()

        if picture:
            album = web.ctx.orm.query(Album).filter(
                Album.id == picture.album_id
            ).first()

            if album.user_id == user_to_update.id:
                # if album.slug == "photos":
                #     if user_to_update.pic_id == picture.id:
                #         user_to_update.pic_obj = self._get_next_picture(album,
                #                                                     picture)
                # elif album.slug == "backgrounds":
                #     if user_to_update.bg_id == picture.id:
                #         user_to_update.bg = self._get_next_picture(album,
                #                                                    picture)
                #         user_to_update.bgx = 0
                #         user_to_update.bgy = 0

                for comment in picture.comments:
                    web.ctx.orm.delete(comment)

                for like in picture.likes:
                    web.ctx.orm.delete(like)

                web.ctx.orm.delete(picture)
                web.ctx.orm.commit()

    def _get_next_picture(self, album, picture):
        for pic in album.pictures:
            if picture.id != pic.id:
                return pic

        return None
