from cryptography.fernet import Fernet 
from typing import *

class CryptoUtils(object):

    def __init__(self) -> None:

        # used to encrypt and decrypt data
        self.crypt = Fernet(Fernet.generate_key())

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