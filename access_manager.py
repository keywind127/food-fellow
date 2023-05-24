from user_manager import UserManager, hash_password_and_salt
from ip_manager import IPManager, IPRecord
from email_manager import GmailManager
from cryptography.fernet import Fernet
from typing import *
import os

class AccessManager:

    ACTIVATION_EXPIRE_TIME = 600

    STATE_LOGIN_SUCCESS = 0
    
    STATE_LOGIN_INVALID = 1

    STATE_LOGIN_NO_USER = 2

    STATE_REGISTER_SUCCESS = 0

    STATE_REGISTER_ALREADY = 1

    STATE_REGISTER_FAILURE = 2

    STATE_ACTIVATE_SUCCESS = 0

    STATE_ACTIVATE_ALREADY = 1

    STATE_ACTIVATE_FAILURE = 2

    BASE_SITE_URL = "http://localhost:127"

    MAX_LOGIN_FAILURES = 5

    def __deco_crypt(crypt_function : Callable) -> Callable:

        def __cryptography(self, data : Any) -> Tuple[ bool, Union[ Any, None ] ]:

            # either encrypt or decrypt
            try:
                return (True, crypt_function(self, data))

            # allow keyboard interrupt
            except (KeyboardInterrupt):
                raise 

            # return (flag == False) on exception
            except (Exception):
                return (False, None)

        return __cryptography

    @__deco_crypt
    def _encrypt_data(self, data : Any) -> str:

        # stringify => binary encoding => encryption => string decoding
        return self.crypt.encrypt(str(data).encode(encoding = "utf-8")).decode(encoding = "utf-8")

    @__deco_crypt 
    def _decrypt_data(self, data : str) -> Any:

        # binary encoding => decryption => string decoding 
        return eval(self.crypt.decrypt(bytes(data, encoding = "utf-8")).decode(encoding = "utf-8"))

    def __init__(self, user_manager  : UserManager, 
                       gmail_manager : GmailManager,
                       ip_manager    : IPManager   ) -> None:

        assert isinstance(user_manager, UserManager)
        
        # used to encrypt and decrypt data
        self.crypt = Fernet(Fernet.generate_key())

        # used to send emails
        self.gmail_manager = gmail_manager

        # used to access user database
        self.user_manager = user_manager

        # used to access login records (of IPs)
        self.ip_manager = ip_manager 

    def _authenticate_login(self, username : str, password : str) -> int:

        # return STATE_LOGIN_NO_ERROR if user does not exist
        if not (self.user_manager.user_exists(username)):
            return self.STATE_LOGIN_NO_USER

        # retrieve hash and salt from user database
        password_hash, password_salt = self.user_manager.fetch_password_and_salt(username)

        # compare computed hash with target hash, and return status code
        #   1. [ 0 ] <=> [ STATE_LOGIN_SUCCESS ]
        #   2. [ 1 ] <=> [ STATE_LOGIN_INVALID ]
        return (hash_password_and_salt(password, password_salt) != password_hash) * 1

    def verify_user_privilege(self, login_username : str, search_username : str) -> bool:

        # verify user is accessing his own info
        return (login_username == search_username)

    def __create_activation_object(self, username : str, password : str) -> Dict[ str, str ]:

        # pack activation data into dictionary
        return {
            "username" : username,
            "password" : password,
            "datetime" : TimeStamp.time2string(TimeStamp.current_time())
        }

    def __activation_object_expired(self, activation_object : Dict[ str, str ]) -> bool:

        # obtain time difference since creation (in seconds)
        timelapse = (TimeStamp.current_time() - TimeStamp.string2time(activation_object["datetime"])).total_seconds()

        # whether timelapse exceeded expiration period
        return (timelapse >= self.ACTIVATION_EXPIRE_TIME)

    def _send_activation_link(self, username : str, password : str) -> bool:

        # email subject
        subject = "Please activate your account."

        # pack activation data then encrypt it
        success, activation_key = self._encrypt_data(self.__create_activation_object(username, password))

        # return (flag == False) if encryption failed
        if not (success):
            return False 

        # obtain activation link 
        #   [ "http://localhost:127", "activate", "ABCD" ] 
        #       => "http://localhost:127/activation?key=ABCD"
        content = os.path.join(self.BASE_SITE_URL, "activate") + f"?key={activation_key}"

        # send the email and return status code
        #   1. [ True  ] <=> [ SUCCESS ]
        #   2. [ False ] <=> [ FAILURE ]
        return self.gmail_manager.send(username, subject, content)

    def register_account(self, username : str, password : str) -> int:

        # check whether user has already registered, returning STATE_REGISTER_ALREADY if true
        if (self.user_manager.user_exists(username)):
            return self.STATE_REGISTER_ALREADY

        # send the activation link to email account, returning STATE_REGISTER_SUCCESS if successful
        if (self._send_activation_link(username, password)):
            return self.STATE_REGISTER_SUCCESS

        # return STATE_REGISTER_FAILURE if unsuccessful
        return self.STATE_REGISTER_FAILURE

    def activate_account(self, activation_key : str) -> int:

        # decrypt activation key
        success, activation_object = self._decrypt_data(activation_key)

        # return STATE_ACTIVATE_FAILURE if decryption failed
        if not (success):
            return self.STATE_ACTIVATE_FAILURE 

        # return STATE_ACTIVATE_FAILURE if past expiration time
        if (self.__activation_object_expired(activation_object)):
            return self.STATE_ACTIVATE_FAILURE

        # return STATE_ACTIVATE_ALREADY if user has already activated
        if (self.user_manager.user_exists(activation_object["username"])):
            return self.STATE_ACTIVATE_ALREADY

        # add user to database
        self.user_manager.add_user(activation_object["username"], activation_object["password"])

        # return STATE_ACTIVATE_SUCCESS after successful activation
        return self.STATE_ACTIVATE_SUCCESS

    def _verify_clean_ip(self, ip_address : str) -> bool:

        # whether or not IP has been blacklisted
        return not self.ip_manager.ip_blacklisted(ip_address)

    def authenticate_login(self, username : str, password : str, ip_address : str) -> int:

        # reject authentication request for blacklisted IP addresses
        if not (self._verify_clean_ip(ip_address)):
            return self.STATE_LOGIN_INVALID

        # attempt to login with username and password
        login_status = self._authenticate_login(username, password)

        # if login was unsuccessful
        if (login_status != self.STATE_LOGIN_SUCCESS):

            # record failed login
            self.ip_manager.add_record(IPRecord(ip_address, is_failure = True))

            # blacklist IP address if number of failures exceeded limit
            if (self.ip_manager.num_failures(ip_address) >= self.MAX_LOGIN_FAILURES):
                self.ip_manager.blacklist_ip(ip_address)

        return login_status

    def trim_ip_history(self) -> None:

        # remove old records
        self.ip_manager._prune_memory()