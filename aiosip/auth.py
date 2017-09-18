from hashlib import md5


def md5digest(*args):
    return md5(':'.join(args).encode()).hexdigest()


import os
import binascii


DEFAULT_ENTROPY = 32


def token_bytes(nbytes=None):
    if nbytes is None:
        nbytes = DEFAULT_ENTROPY
    return os.urandom(nbytes)


def token_hex(nbytes=None):
    return binascii.hexlify(token_bytes(nbytes)).decode('ascii')


def generate_nonce():
    return token_hex()


class WWWAuth(dict):
    def __init__(self, method, realm, opaque=None, nonce=None, qop='auth',
                 algorithm='MD5', stale='false'):
        if not opaque:
            opaque = str(generate_nonce())
        if not nonce:
            nonce = str(generate_nonce())

        self.method = method
        super().__init__({'realm': realm,
                          'qop': qop,
                          'opaque': opaque,
                          'nonce': nonce,
                          'algorithm': algorithm,
                          'stale': stale})

    @classmethod
    def from_header(cls, header):
        if not header.startswith('Digest'):
            raise ValueError('Authentication method not supported')

        auth = {}
        params = header[7:].split(',')
        for param in params:
            k, v = param.split('=')
            if '="' in param:
                v = v[1:-1]
            auth[k] = v

        return cls('Digest', **auth)

    def __str__(self):
        if self.method != 'Digest':
            raise ValueError('Authentication method not supported')

        segments = []
        for key, value in self.items():
            if key == 'algorithm':
                segments.append('%s=%s' % (key, value))
            else:
                segments.append('%s="%s"' % (key, value))

        return 'Digest ' + ','.join(segments)


class Auth(dict):
    def __init__(self, method, realm, username, password, uri, nonce):
        self.method = method

        ha1 = md5digest(username, realm, password)
        ha2 = md5digest(method, uri)
        response = md5digest(ha1, nonce, ha2)
        super().__init__({'username': username,
                          'uri': uri,
                          'realm': realm,
                          'nonce': nonce,
                          'response': response})

    def __str__(self):
        if self.method != 'Digest':
            raise ValueError('Authentication method not supported')

        segments = []
        for key, value in self.items():
            if key == 'algorithm':
                segments.append('%s=%s' % (key, value))
            else:
                segments.append('%s="%s"' % (key, value))

        return 'Digest ' + ','.join(segments)

    @classmethod
    def from_authenticate_header(cls, header, uri, username, password):
        if header.method != 'Digest':
            raise ValueError('Authentication method not supported')

        return cls('Digest', header['realm'], uri, username, password,
                   header['nonce'])
