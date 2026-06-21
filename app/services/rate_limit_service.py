from collections import defaultdict

import time


requests_map = defaultdict(list)

def allow_request(

    ip,

    max_requests=30,

    window=60

):
    now = time.time()

    requests_map[ip] = [

        t

        for t

        in requests_map[ip]

        if now - t < window

    ]

    if len(

            requests_map[ip]

    ) >= max_requests:
        return False