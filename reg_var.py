import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import binascii
import json

import pymysql

class Register:
    def __init__(self,pid):
        self.pid = pid
        self.wallet_address = ""
        self.private_key = ""
        self.public_key = ""
        self.amount = 0
    
    def RSA_generation(self):
        random_gen = Crypto.Random.new().read
        private_seed = RSA.generate(1024, random_gen)
        public_seed = private_seed.publickey()

        self.private_key = binascii.hexlify(private_seed.exportKey('DER')).decode('ascii')
        self.public_key = binascii.hexlify(public_seed.exportKey('DER')).decode('ascii')

    def mysql_record(self):
        db = pymysql.connect("13.78.37.166","root","blockchainisgood","blockchain" )
        cursor = db.cursor()

        sql = "INSERT INTO user_information(pid, \
               private, public ,amount) \
               VALUES (%s,%s,%s,0)"
        try:
            cursor.execute(sql,(self.pid,self.private_key,self.public_key))
            db.commit()
        except:
            db.rollback()
        
        db.close()
    
    def new_wallet(self):
        self.RSA_generation()
        self.mysql_record()
        self.wallet_address = self.public_key

class Sign:
    def __init__(self,private_key,transaction):
        self.private_key = private_key
        self.transaction = transaction
    
    def sign(self):
        encodekey = RSA.importKey(binascii.unhexlify(self.private_key))
        signer = PKCS1_v1_5.new(encodekey)
        transaction_string = json.dumps(self.transaction, sort_keys=True).encode("utf8")
        message = SHA.new(transaction_string)
        cipher = binascii.hexlify(signer.sign(message)).decode('ascii')

        return cipher

class Verify:
    def __init__(self,wallet_address,transaction,cipher):
        self.public_key = wallet_address
        self.transaction = transaction
        self.cipher = cipher

    def verify(self):
        decodekey = RSA.importKey(binascii.unhexlify(self.public_key))
        verifier = PKCS1_v1_5.new(decodekey)
        transaction_string = json.dumps(self.transaction, sort_keys=True).encode("utf8")
        message = SHA.new(transaction_string)
        
        return verifier.verify(message,binascii.unhexlify(self.cipher))

