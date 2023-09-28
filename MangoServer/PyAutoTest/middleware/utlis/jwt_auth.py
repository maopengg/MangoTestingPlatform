# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-01 22:26
# @Author : 毛鹏
import datetime

import jwt
from django.conf import settings


def create_token(payload, timeout=720):
    salt = settings.SECRET_KEY
    headers = {
        'type': 'jwt',
        'alg': 'HS256'
    }
    payload['exp'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=timeout)
    return jwt.encode(
        payload=payload, key=salt, algorithm='HS256', headers=headers).encode('utf-8')
